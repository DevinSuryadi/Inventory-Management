-- =====================================================
-- FILE 7: CREATE FUNCTION - IMPORT & VIEW
-- (JALANKAN KETUJUH - TERAKHIR)
-- =====================================================

-- FUNGSI BULK IMPORT SMART
-- CATATAN: Fungsi ini menggunakan TEXT untuk semua parameter tanggal
-- untuk menghindari error duplikasi (PGRST203)
CREATE OR REPLACE FUNCTION bulk_import_smart(
    p_store TEXT,
    p_supplier_id INTEGER,
    p_warehouse_id INTEGER,
    p_products TEXT,
    p_account_id INTEGER DEFAULT NULL,
    p_payment_type TEXT DEFAULT 'cash',
    p_payment_amount NUMERIC DEFAULT NULL,
    p_import_date TEXT DEFAULT NULL,
    p_created_by TEXT DEFAULT 'system'
)
RETURNS TABLE (
    new_count INTEGER,
    existing_count INTEGER,
    total_count INTEGER,
    transaction_id INTEGER
) AS $$
DECLARE
    v_products JSONB;
    v_product JSONB;
    v_product_id INTEGER;
    v_warehouse_id INTEGER;
    v_new_count INTEGER := 0;
    v_existing_count INTEGER := 0;
    v_total_amount NUMERIC := 0;
    v_transaction_id INTEGER;
    v_import_date TIMESTAMP;
    v_balance_after NUMERIC;
    v_paid_amount NUMERIC;
    v_debt_amount NUMERIC;
BEGIN
    -- Parse import date
    IF p_import_date IS NOT NULL AND p_import_date != '' THEN
        v_import_date := p_import_date::TIMESTAMP;
    ELSE
        v_import_date := CURRENT_TIMESTAMP;
    END IF;
    
    v_products := p_products::JSONB;
    v_warehouse_id := p_warehouse_id;
    
    -- Proses setiap produk
    FOR v_product IN SELECT * FROM jsonb_array_elements(v_products)
    LOOP
        -- Cek apakah produk sudah ada (berdasarkan SKU dan store)
        SELECT productid INTO v_product_id
        FROM product 
        WHERE sku = (v_product->>'sku') AND store = p_store;
        
        IF v_product_id IS NULL THEN
            -- Produk baru
            INSERT INTO product (
                productname, sku, barcode, category, purchaseprice, 
                sellingprice, quantity, minquantity, unit, store, createat, updateat
            )
            VALUES (
                v_product->>'productname',
                v_product->>'sku',
                v_product->>'barcode',
                COALESCE(v_product->>'category', 'Umum'),
                COALESCE((v_product->>'purchaseprice')::NUMERIC, 0),
                COALESCE((v_product->>'sellingprice')::NUMERIC, 0),
                COALESCE((v_product->>'quantity')::INTEGER, 0),
                COALESCE((v_product->>'minquantity')::INTEGER, 5),
                COALESCE(v_product->>'unit', 'pcs'),
                p_store,
                v_import_date,
                v_import_date
            )
            RETURNING productid INTO v_product_id;
            
            v_new_count := v_new_count + 1;
        ELSE
            -- Update produk yang sudah ada
            UPDATE product SET
                productname = COALESCE(v_product->>'productname', productname),
                barcode = COALESCE(v_product->>'barcode', barcode),
                category = COALESCE(v_product->>'category', category),
                purchaseprice = COALESCE((v_product->>'purchaseprice')::NUMERIC, purchaseprice),
                sellingprice = COALESCE((v_product->>'sellingprice')::NUMERIC, sellingprice),
                quantity = quantity + COALESCE((v_product->>'quantity')::INTEGER, 0),
                minquantity = COALESCE((v_product->>'minquantity')::INTEGER, minquantity),
                unit = COALESCE(v_product->>'unit', unit),
                updateat = v_import_date
            WHERE productid = v_product_id;
            
            v_existing_count := v_existing_count + 1;
        END IF;
        
        -- Update product_warehouse
        INSERT INTO product_warehouse (productid, warehouseid, quantity)
        VALUES (v_product_id, v_warehouse_id, COALESCE((v_product->>'quantity')::INTEGER, 0))
        ON CONFLICT (productid, warehouseid) 
        DO UPDATE SET quantity = product_warehouse.quantity + COALESCE((v_product->>'quantity')::INTEGER, 0);
        
        -- Hitung total amount
        v_total_amount := v_total_amount + (COALESCE((v_product->>'purchaseprice')::NUMERIC, 0) * COALESCE((v_product->>'quantity')::INTEGER, 0));
    END LOOP;
    
    -- Buat transaksi jika total > 0
    IF v_total_amount > 0 THEN
        INSERT INTO transaction (store, type, date, totalamount)
        VALUES (p_store, 'import', v_import_date, v_total_amount)
        RETURNING transactionid INTO v_transaction_id;
        
        -- Tentukan jumlah bayar dan hutang
        IF p_payment_type = 'cash' THEN
            v_paid_amount := v_total_amount;
            v_debt_amount := 0;
        ELSIF p_payment_type = 'partial' THEN
            v_paid_amount := COALESCE(p_payment_amount, 0);
            v_debt_amount := v_total_amount - v_paid_amount;
        ELSE -- credit
            v_paid_amount := 0;
            v_debt_amount := v_total_amount;
        END IF;
        
        -- Insert ke purchase
        INSERT INTO purchase (
            transactionid, supplierid, warehouseid, paymenttype,
            totalamount, paidamount, transactiondate, createdby
        )
        VALUES (
            v_transaction_id, p_supplier_id, v_warehouse_id, p_payment_type,
            v_total_amount, v_paid_amount, v_import_date, p_created_by
        );
        
        -- Jika ada pembayaran cash dan ada akun
        IF v_paid_amount > 0 AND p_account_id IS NOT NULL THEN
            UPDATE accounts SET balance = balance - v_paid_amount
            WHERE account_id = p_account_id
            RETURNING balance INTO v_balance_after;
            
            INSERT INTO account_transactions (
                account_id, transaction_type, related_id, amount,
                balance_after, description, transaction_date, created_by
            )
            VALUES (
                p_account_id, 'import', v_transaction_id, -v_paid_amount,
                v_balance_after, 'Import stok dari supplier', v_import_date, p_created_by
            );
        END IF;
        
        -- Jika ada hutang, buat record debt
        IF v_debt_amount > 0 THEN
            INSERT INTO debt (
                store, type, relatedid, relatedname, 
                amount, paid, date, note
            )
            SELECT 
                p_store, 'supplier', p_supplier_id, s.suppliername,
                v_debt_amount, 0, v_import_date, 'Import stok'
            FROM supplier s WHERE s.supplierid = p_supplier_id;
        END IF;
    END IF;
    
    RETURN QUERY SELECT v_new_count, v_existing_count, v_new_count + v_existing_count, v_transaction_id;
END;
$$ LANGUAGE plpgsql;

-- FUNGSI GET SUPPLIERS VIEW
CREATE OR REPLACE FUNCTION get_suppliers_view(p_store TEXT)
RETURNS TABLE (
    supplierid INTEGER,
    suppliername TEXT,
    supplierno TEXT,
    address TEXT,
    description TEXT,
    total_debt NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        s.supplierid,
        s.suppliername::TEXT,
        s.supplierno::TEXT,
        s.address::TEXT,
        s.description::TEXT,
        COALESCE(SUM(d.amount - d.paid), 0)::NUMERIC as total_debt
    FROM supplier s
    LEFT JOIN debt d ON d.type = 'supplier' AND d.relatedid = s.supplierid AND d.store = p_store
    WHERE s.store = p_store
    GROUP BY s.supplierid, s.suppliername, s.supplierno, s.address, s.description
    ORDER BY s.suppliername;
END;
$$ LANGUAGE plpgsql;

-- FUNGSI GET LOW STOCK PRODUCTS
CREATE OR REPLACE FUNCTION get_low_stock_products(p_store TEXT)
RETURNS TABLE (
    product_id INTEGER,
    product_name TEXT,
    sku TEXT,
    current_quantity INTEGER,
    min_quantity INTEGER,
    unit TEXT,
    category TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        p.productid::INTEGER as product_id,
        p.productname::TEXT as product_name,
        p.sku::TEXT,
        p.quantity::INTEGER as current_quantity,
        p.minquantity::INTEGER as min_quantity,
        p.unit::TEXT,
        p.category::TEXT
    FROM product p
    WHERE p.store = p_store AND p.quantity <= p.minquantity
    ORDER BY (p.quantity::FLOAT / NULLIF(p.minquantity, 0)) ASC;
END;
$$ LANGUAGE plpgsql;

-- FUNGSI GET PRODUCT MOVEMENT HISTORY
CREATE OR REPLACE FUNCTION get_product_movement_history(
    p_product_id INTEGER,
    p_start_date DATE DEFAULT NULL,
    p_end_date DATE DEFAULT NULL
)
RETURNS TABLE (
    movement_date TIMESTAMP,
    movement_type TEXT,
    quantity INTEGER,
    reference_id INTEGER,
    notes TEXT
) AS $$
BEGIN
    RETURN QUERY
    -- Stock adjustments
    SELECT 
        sa.adjustment_date as movement_date,
        'adjustment'::TEXT as movement_type,
        CASE WHEN sa.adjustment_type = 'add' THEN sa.quantity ELSE -sa.quantity END as quantity,
        sa.adjustment_id as reference_id,
        sa.reason::TEXT as notes
    FROM stock_adjustment sa
    WHERE sa.product_id = p_product_id
        AND (p_start_date IS NULL OR DATE(sa.adjustment_date) >= p_start_date)
        AND (p_end_date IS NULL OR DATE(sa.adjustment_date) <= p_end_date)
    
    UNION ALL
    
    -- Purchases
    SELECT 
        p.transactiondate as movement_date,
        'purchase'::TEXT as movement_type,
        pi.quantity as quantity,
        p.purchaseid as reference_id,
        'Pembelian'::TEXT as notes
    FROM purchase_items pi
    JOIN purchase p ON pi.purchaseid = p.purchaseid
    WHERE pi.productid = p_product_id
        AND (p_start_date IS NULL OR DATE(p.transactiondate) >= p_start_date)
        AND (p_end_date IS NULL OR DATE(p.transactiondate) <= p_end_date)
    
    UNION ALL
    
    -- Sales
    SELECT 
        s.transactiondate as movement_date,
        'sale'::TEXT as movement_type,
        -si.quantity as quantity,
        s.saleid as reference_id,
        'Penjualan'::TEXT as notes
    FROM sale_items si
    JOIN sale s ON si.saleid = s.saleid
    WHERE si.productid = p_product_id
        AND (p_start_date IS NULL OR DATE(s.transactiondate) >= p_start_date)
        AND (p_end_date IS NULL OR DATE(s.transactiondate) <= p_end_date)
    
    ORDER BY movement_date DESC;
END;
$$ LANGUAGE plpgsql;

SELECT 'SEMUA FUNCTION SELESAI DIBUAT!' as status;
