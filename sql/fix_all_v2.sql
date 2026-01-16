-- =====================================================
-- FIX ALL FUNCTIONS - Parameter store_input
-- Jalankan di Supabase SQL Editor
-- =====================================================

-- 1. DROP semua fungsi yang bermasalah (explicit drops)
DROP FUNCTION IF EXISTS get_supplier_debts(TEXT) CASCADE;
DROP FUNCTION IF EXISTS get_supplier_debts_with_top(TEXT) CASCADE;
DROP FUNCTION IF EXISTS get_customer_debts(TEXT) CASCADE;
DROP FUNCTION IF EXISTS get_customer_debts_with_top(TEXT) CASCADE;
DROP FUNCTION IF EXISTS bulk_import_smart(TEXT, INTEGER, INTEGER, TEXT, INTEGER, TEXT, NUMERIC, TEXT, TEXT) CASCADE;
DROP FUNCTION IF EXISTS create_default_cash_account(TEXT) CASCADE;
DROP FUNCTION IF EXISTS get_suppliers_view(TEXT) CASCADE;

-- Drop dengan dynamic SQL untuk memastikan semua versi terhapus
DO $$
DECLARE
    funcs TEXT[] := ARRAY[
        'get_supplier_debts',
        'get_supplier_debts_with_top',
        'get_customer_debts',
        'get_customer_debts_with_top',
        'bulk_import_smart',
        'create_default_cash_account',
        'get_suppliers_view'
    ];
    func_name TEXT;
    rec RECORD;
    drop_cmd TEXT;
BEGIN   
    FOREACH func_name IN ARRAY funcs
    LOOP
        FOR rec IN 
            SELECT p.oid::regprocedure::TEXT as func_sig
            FROM pg_proc p
            JOIN pg_namespace n ON p.pronamespace = n.oid
            WHERE n.nspname = 'public' AND p.proname = func_name
        LOOP
            drop_cmd := 'DROP FUNCTION IF EXISTS ' || rec.func_sig || ' CASCADE';
            EXECUTE drop_cmd;
            RAISE NOTICE 'Dropped: %', rec.func_sig;
        END LOOP;
    END LOOP;
END $$;

-- 2. FUNGSI GET SUPPLIER DEBTS
-- Struktur tabel debt: debtid, type, relatedid, amount, paid, date, description, store, due_date
CREATE OR REPLACE FUNCTION get_supplier_debts(p_store TEXT)
RETURNS TABLE (
    debtid INTEGER,
    supplier_name VARCHAR,
    total_debt NUMERIC,
    paid_amount NUMERIC,
    remaining_debt NUMERIC,
    debt_date TIMESTAMP,
    purchase_description TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        d.debtid,
        s.suppliername,
        d.amount AS total_debt,
        d.paid AS paid_amount,
        (d.amount - d.paid) AS remaining_debt,
        d.date AS debt_date,
        d.description AS purchase_description
    FROM debt d
    JOIN supplier s ON d.relatedid = s.supplierid
    WHERE d.type = 'supplier'
      AND d.store = p_store
      AND (d.amount - d.paid) > 0
    ORDER BY d.date DESC;
END;
$$ LANGUAGE plpgsql;

-- 3. FUNGSI GET SUPPLIER DEBTS WITH TOP
CREATE OR REPLACE FUNCTION get_supplier_debts_with_top(p_store TEXT)
RETURNS TABLE (
    debtid INTEGER,
    supplier_name VARCHAR,
    total_debt NUMERIC,
    paid_amount NUMERIC,
    remaining_debt NUMERIC,
    debt_date TIMESTAMP,
    due_date TIMESTAMP,
    days_until_due INTEGER,
    purchase_description TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        d.debtid,
        s.suppliername,
        d.amount AS total_debt,
        d.paid AS paid_amount,
        (d.amount - d.paid) AS remaining_debt,
        d.date AS debt_date,
        d.due_date,
        EXTRACT(DAY FROM (d.due_date - CURRENT_TIMESTAMP))::INTEGER AS days_until_due,
        d.description AS purchase_description
    FROM debt d
    JOIN supplier s ON d.relatedid = s.supplierid
    WHERE d.type = 'supplier'
      AND d.store = p_store
      AND (d.amount - d.paid) > 0
    ORDER BY d.date DESC;
END;
$$ LANGUAGE plpgsql;

-- 4. FUNGSI GET CUSTOMER DEBTS
-- Untuk customer, kita ambil customer_name dari description atau sale_transaction
CREATE OR REPLACE FUNCTION get_customer_debts(p_store TEXT)
RETURNS TABLE (
    debtid INTEGER,
    customer_name VARCHAR,
    total_debt NUMERIC,
    paid_amount NUMERIC,
    remaining_debt NUMERIC,
    debt_date TIMESTAMP,
    sale_description TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        d.debtid,
        COALESCE(st.customer_name, 'Pelanggan')::VARCHAR AS customer_name,
        d.amount AS total_debt,
        d.paid AS paid_amount,
        (d.amount - d.paid) AS remaining_debt,
        d.date AS debt_date,
        d.description AS sale_description
    FROM debt d
    LEFT JOIN sale_transaction st ON d.relatedid = st.transaction_id
    WHERE d.type = 'customer'
      AND d.store = p_store
      AND (d.amount - d.paid) > 0
    ORDER BY d.date DESC;
END;
$$ LANGUAGE plpgsql;

-- 5. FUNGSI GET CUSTOMER DEBTS WITH TOP
CREATE OR REPLACE FUNCTION get_customer_debts_with_top(p_store TEXT)
RETURNS TABLE (
    debtid INTEGER,
    customer_name VARCHAR,
    total_debt NUMERIC,
    paid_amount NUMERIC,
    remaining_debt NUMERIC,
    debt_date TIMESTAMP,
    due_date TIMESTAMP,
    days_until_due INTEGER,
    sale_description TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        d.debtid,
        COALESCE(st.customer_name, 'Pelanggan')::VARCHAR AS customer_name,
        d.amount AS total_debt,
        d.paid AS paid_amount,
        (d.amount - d.paid) AS remaining_debt,
        d.date AS debt_date,
        d.due_date,
        EXTRACT(DAY FROM (d.due_date - CURRENT_TIMESTAMP))::INTEGER AS days_until_due,
        d.description AS sale_description
    FROM debt d
    LEFT JOIN sale_transaction st ON d.relatedid = st.transaction_id
    WHERE d.type = 'customer'
      AND d.store = p_store
      AND (d.amount - d.paid) > 0
    ORDER BY d.date DESC;
END;
$$ LANGUAGE plpgsql;

-- Tambahan: Buat fungsi dengan parameter store_input juga (untuk backward compatibility)
CREATE OR REPLACE FUNCTION get_supplier_debts(store_input TEXT)
RETURNS TABLE (
    debtid INTEGER,
    supplier_name VARCHAR,
    total_debt NUMERIC,
    paid_amount NUMERIC,
    remaining_debt NUMERIC,
    debt_date TIMESTAMP,
    purchase_description TEXT
) AS $$
BEGIN
    RETURN QUERY SELECT * FROM get_supplier_debts(p_store := store_input);
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION get_supplier_debts_with_top(store_input TEXT)
RETURNS TABLE (
    debtid INTEGER,
    supplier_name VARCHAR,
    total_debt NUMERIC,
    paid_amount NUMERIC,
    remaining_debt NUMERIC,
    debt_date TIMESTAMP,
    due_date TIMESTAMP,
    days_until_due INTEGER,
    purchase_description TEXT
) AS $$
BEGIN
    RETURN QUERY SELECT * FROM get_supplier_debts_with_top(p_store := store_input);
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION get_customer_debts(store_input TEXT)
RETURNS TABLE (
    debtid INTEGER,
    customer_name VARCHAR,
    total_debt NUMERIC,
    paid_amount NUMERIC,
    remaining_debt NUMERIC,
    debt_date TIMESTAMP,
    sale_description TEXT
) AS $$
BEGIN
    RETURN QUERY SELECT * FROM get_customer_debts(p_store := store_input);
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION get_customer_debts_with_top(store_input TEXT)
RETURNS TABLE (
    debtid INTEGER,
    customer_name VARCHAR,
    total_debt NUMERIC,
    paid_amount NUMERIC,
    remaining_debt NUMERIC,
    debt_date TIMESTAMP,
    due_date TIMESTAMP,
    days_until_due INTEGER,
    sale_description TEXT
) AS $$
BEGIN
    RETURN QUERY SELECT * FROM get_customer_debts_with_top(p_store := store_input);
END;
$$ LANGUAGE plpgsql;

-- 6. FUNGSI BULK IMPORT SMART
-- Struktur purchase_transaction: transaction_id, store, supplier_id, warehouse_id, 
--   total_amount, payment_type, due_date, account_id, description, transaction_date, created_by, created_at
-- TIDAK ADA: paid_amount, purchase_id
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
    v_new_count INTEGER := 0;
    v_existing_count INTEGER := 0;
    v_total_amount NUMERIC := 0;
    v_transaction_id INTEGER;
    v_import_date TIMESTAMP;
    v_balance_after NUMERIC;
    v_paid_amount NUMERIC;
    v_debt_amount NUMERIC;
    v_purchase_price NUMERIC;
    v_quantity INTEGER;
BEGIN
    IF p_import_date IS NOT NULL AND p_import_date != '' THEN
        v_import_date := p_import_date::TIMESTAMP;
    ELSE
        v_import_date := CURRENT_TIMESTAMP;
    END IF;
    
    v_products := p_products::JSONB;
    
    FOR v_product IN SELECT * FROM jsonb_array_elements(v_products)
    LOOP
        v_purchase_price := COALESCE((v_product->>'purchaseprice')::NUMERIC, (v_product->>'harga')::NUMERIC, 0);
        v_quantity := COALESCE((v_product->>'quantity')::INTEGER, 0);
        
        -- Cek produk berdasarkan nama dan store
        SELECT productid INTO v_product_id
        FROM product 
        WHERE productname = (v_product->>'productname') AND store = p_store;
        
        IF v_product_id IS NULL THEN
            -- Produk baru
            INSERT INTO product (
                productname, store, type, color, harga, quantity, 
                description, size, brand, updateat
            )
            VALUES (
                v_product->>'productname',
                p_store,
                COALESCE(v_product->>'type', v_product->>'category', 'Umum'),
                v_product->>'color',
                v_purchase_price,
                v_quantity,
                v_product->>'description',
                v_product->>'size',
                v_product->>'brand',
                v_import_date
            )
            RETURNING productid INTO v_product_id;
            
            v_new_count := v_new_count + 1;
        ELSE
            -- Update produk (weighted average price)
            UPDATE product SET
                type = COALESCE(NULLIF(v_product->>'type', ''), NULLIF(v_product->>'category', ''), type),
                color = COALESCE(NULLIF(v_product->>'color', ''), color),
                harga = CASE 
                    WHEN quantity + v_quantity > 0 THEN 
                        ((COALESCE(harga, 0) * quantity) + (v_purchase_price * v_quantity)) / (quantity + v_quantity)
                    ELSE v_purchase_price
                END,
                quantity = quantity + v_quantity,
                description = COALESCE(NULLIF(v_product->>'description', ''), description),
                size = COALESCE(NULLIF(v_product->>'size', ''), size),
                brand = COALESCE(NULLIF(v_product->>'brand', ''), brand),
                updateat = v_import_date
            WHERE productid = v_product_id;
            
            v_existing_count := v_existing_count + 1;
        END IF;
        
        -- Update product_warehouse
        INSERT INTO product_warehouse (productid, warehouseid, quantity)
        VALUES (v_product_id, p_warehouse_id, v_quantity)
        ON CONFLICT (productid, warehouseid) 
        DO UPDATE SET quantity = product_warehouse.quantity + v_quantity;
        
        v_total_amount := v_total_amount + (v_purchase_price * v_quantity);
    END LOOP;
    
    -- Buat purchase transaction jika total > 0
    IF v_total_amount > 0 THEN
        IF p_payment_type = 'cash' THEN
            v_paid_amount := v_total_amount;
            v_debt_amount := 0;
        ELSIF p_payment_type = 'partial' THEN
            v_paid_amount := COALESCE(p_payment_amount, 0);
            v_debt_amount := v_total_amount - v_paid_amount;
        ELSE
            v_paid_amount := 0;
            v_debt_amount := v_total_amount;
        END IF;
        
        -- Insert ke purchase_transaction (sesuai struktur tabel)
        INSERT INTO purchase_transaction (
            store, supplier_id, warehouse_id, payment_type,
            total_amount, account_id, description, transaction_date, created_by
        )
        VALUES (
            p_store, p_supplier_id, p_warehouse_id, p_payment_type,
            v_total_amount, p_account_id, 'Import stok dari Excel', v_import_date, p_created_by
        )
        RETURNING purchase_transaction.transaction_id INTO v_transaction_id;
        
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
                p_account_id, 'purchase', v_transaction_id, -v_paid_amount,
                v_balance_after, 'Import stok dari supplier', v_import_date, p_created_by
            );
        END IF;
        
        -- Jika ada hutang, buat record debt
        IF v_debt_amount > 0 THEN
            INSERT INTO debt (
                store, type, relatedid, 
                amount, paid, date, description
            )
            VALUES (
                p_store, 'supplier', p_supplier_id,
                v_debt_amount, 0, v_import_date, 'Import stok dari Excel'
            );
        END IF;
    END IF;
    
    RETURN QUERY SELECT v_new_count, v_existing_count, v_new_count + v_existing_count, v_transaction_id;
END;
$$ LANGUAGE plpgsql;

-- 7. FUNGSI CREATE DEFAULT CASH ACCOUNT
CREATE OR REPLACE FUNCTION create_default_cash_account(p_store_name TEXT)
RETURNS VOID AS $$
BEGIN
    -- Check if default cash account exists, if not create it
    IF NOT EXISTS (
        SELECT 1 FROM accounts 
        WHERE store = p_store_name AND is_default = TRUE
    ) THEN
        INSERT INTO accounts (store, account_name, account_type, balance, is_default)
        VALUES (p_store_name, 'Kas Toko', 'cash', 0, TRUE);
    END IF;
END;
$$ LANGUAGE plpgsql;

-- 8. FUNGSI GET SUPPLIERS VIEW
CREATE OR REPLACE FUNCTION get_suppliers_view(store_input TEXT)
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
    LEFT JOIN debt d ON d.type = 'supplier' AND d.relatedid = s.supplierid AND d.store = store_input
    WHERE s.store = store_input
    GROUP BY s.supplierid, s.suppliername, s.supplierno, s.address, s.description
    ORDER BY s.suppliername;
END;
$$ LANGUAGE plpgsql;

-- 9. Verifikasi
SELECT 'Semua fungsi berhasil dibuat!' as status;

SELECT proname, pg_get_function_arguments(oid) as arguments
FROM pg_proc 
WHERE proname IN ('get_supplier_debts', 'get_supplier_debts_with_top', 
                  'get_customer_debts', 'get_customer_debts_with_top',
                  'bulk_import_smart', 'create_default_cash_account', 'get_suppliers_view')
AND pronamespace = 'public'::regnamespace;
