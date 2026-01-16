-- =====================================================
-- QUICK FIX: Perbaikan Fungsi get_suppliers_view dan bulk_import_smart
-- Jalankan script ini di Supabase SQL Editor
-- =====================================================

-- 1. DROP semua versi fungsi yang ada
DO $$
DECLARE
    rec RECORD;
    drop_cmd TEXT;
BEGIN
    -- Drop all versions of get_suppliers_view
    FOR rec IN 
        SELECT p.oid::regprocedure::TEXT as func_sig
        FROM pg_proc p
        JOIN pg_namespace n ON p.pronamespace = n.oid
        WHERE n.nspname = 'public' AND p.proname = 'get_suppliers_view'
    LOOP
        drop_cmd := 'DROP FUNCTION IF EXISTS ' || rec.func_sig || ' CASCADE';
        EXECUTE drop_cmd;
        RAISE NOTICE 'Dropped: %', rec.func_sig;
    END LOOP;
    
    -- Drop all versions of bulk_import_smart
    FOR rec IN 
        SELECT p.oid::regprocedure::TEXT as func_sig
        FROM pg_proc p
        JOIN pg_namespace n ON p.pronamespace = n.oid
        WHERE n.nspname = 'public' AND p.proname = 'bulk_import_smart'
    LOOP
        drop_cmd := 'DROP FUNCTION IF EXISTS ' || rec.func_sig || ' CASCADE';
        EXECUTE drop_cmd;
        RAISE NOTICE 'Dropped: %', rec.func_sig;
    END LOOP;
END $$;

-- 2. Buat ulang fungsi get_suppliers_view
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

-- 3. Buat ulang fungsi bulk_import_smart
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

-- 4. Verifikasi
SELECT 'Fungsi berhasil dibuat!' as status;

-- Cek fungsi yang ada
SELECT proname, pg_get_function_arguments(oid) as arguments
FROM pg_proc 
WHERE proname IN ('get_suppliers_view', 'bulk_import_smart')
AND pronamespace = 'public'::regnamespace;
