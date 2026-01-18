-- =====================================================
-- MIGRATION V2: Fitur Baru
-- - No Nota untuk penjualan dan pembelian
-- - Penjualan & Pembelian Lainnya (non-stok)
-- Jalankan di Supabase SQL Editor
-- =====================================================

-- 1. Tambah kolom invoice_number ke purchase_transaction
ALTER TABLE purchase_transaction ADD COLUMN IF NOT EXISTS invoice_number VARCHAR;

-- 2. Tambah kolom invoice_number ke sale_transaction
ALTER TABLE sale_transaction ADD COLUMN IF NOT EXISTS invoice_number VARCHAR;

-- 3. Tambah kolom invoice_number ke tabel purchase (untuk riwayat)
ALTER TABLE purchase ADD COLUMN IF NOT EXISTS invoice_number VARCHAR;

-- 4. Tambah kolom invoice_number ke tabel sale (untuk riwayat)
ALTER TABLE sale ADD COLUMN IF NOT EXISTS invoice_number VARCHAR;

-- 5. Tambah kolom is_non_stock ke purchase_transaction (untuk pembelian lainnya)
ALTER TABLE purchase_transaction ADD COLUMN IF NOT EXISTS is_non_stock BOOLEAN DEFAULT FALSE;

-- 6. Tambah kolom is_non_stock ke sale_transaction (untuk penjualan lainnya)
ALTER TABLE sale_transaction ADD COLUMN IF NOT EXISTS is_non_stock BOOLEAN DEFAULT FALSE;

-- 7. Tambah kolom is_non_stock ke purchase
ALTER TABLE purchase ADD COLUMN IF NOT EXISTS is_non_stock BOOLEAN DEFAULT FALSE;

-- 8. Tambah kolom is_non_stock ke sale
ALTER TABLE sale ADD COLUMN IF NOT EXISTS is_non_stock BOOLEAN DEFAULT FALSE;

-- 9. Tambah kolom item_name ke purchase (untuk pembelian non-stok tanpa productid)
ALTER TABLE purchase ADD COLUMN IF NOT EXISTS item_name VARCHAR;
ALTER TABLE purchase ADD COLUMN IF NOT EXISTS item_type VARCHAR;

-- 10. Tambah kolom item_name ke sale (untuk penjualan non-stok tanpa productid)
ALTER TABLE sale ADD COLUMN IF NOT EXISTS item_name VARCHAR;
ALTER TABLE sale ADD COLUMN IF NOT EXISTS item_type VARCHAR;

-- 11. Tambah kolom store ke purchase dan sale untuk non-stok
ALTER TABLE purchase ADD COLUMN IF NOT EXISTS store TEXT;
ALTER TABLE sale ADD COLUMN IF NOT EXISTS store TEXT;

-- 12. Index untuk pencarian invoice_number
CREATE INDEX IF NOT EXISTS idx_purchase_transaction_invoice ON purchase_transaction(invoice_number);
CREATE INDEX IF NOT EXISTS idx_sale_transaction_invoice ON sale_transaction(invoice_number);
CREATE INDEX IF NOT EXISTS idx_purchase_invoice ON purchase(invoice_number);
CREATE INDEX IF NOT EXISTS idx_sale_invoice ON sale(invoice_number);

-- =====================================================
-- UPDATE FUNCTIONS
-- =====================================================

-- Drop existing functions first
DROP FUNCTION IF EXISTS record_purchase_transaction_multi(TEXT, INTEGER, INTEGER, TEXT, TEXT, TEXT, INTEGER, TEXT, TEXT, TEXT) CASCADE;
DROP FUNCTION IF EXISTS record_purchase_transaction_multi(TEXT, INTEGER, INTEGER, TEXT, TEXT, TEXT, INTEGER, TEXT, TEXT, TEXT, TEXT) CASCADE;
DROP FUNCTION IF EXISTS record_sale_transaction_multi(TEXT, INTEGER, TEXT, TEXT, TEXT, TEXT, INTEGER, TEXT, TEXT, TEXT) CASCADE;
DROP FUNCTION IF EXISTS record_sale_transaction_multi(TEXT, INTEGER, TEXT, TEXT, TEXT, TEXT, INTEGER, TEXT, TEXT, TEXT, TEXT) CASCADE;
DROP FUNCTION IF EXISTS record_other_purchase(TEXT, TEXT, TEXT, TEXT, INTEGER, NUMERIC, TEXT, TEXT, INTEGER, TEXT, TEXT, TEXT) CASCADE;
DROP FUNCTION IF EXISTS record_other_sale(TEXT, TEXT, TEXT, TEXT, INTEGER, NUMERIC, TEXT, TEXT, INTEGER, TEXT, TEXT, TEXT) CASCADE;
DROP FUNCTION IF EXISTS get_purchase_history(TEXT, TEXT, TEXT) CASCADE;
DROP FUNCTION IF EXISTS get_sale_history(TEXT, TEXT, TEXT) CASCADE;

-- Dynamic drop
DO $$
DECLARE
    funcs TEXT[] := ARRAY[
        'record_purchase_transaction_multi',
        'record_sale_transaction_multi',
        'record_other_purchase',
        'record_other_sale',
        'get_purchase_history',
        'get_sale_history'
    ];
    func_name TEXT;
    rec RECORD;
BEGIN   
    FOREACH func_name IN ARRAY funcs
    LOOP
        FOR rec IN 
            SELECT p.oid::regprocedure::TEXT as func_sig
            FROM pg_proc p
            JOIN pg_namespace n ON p.pronamespace = n.oid
            WHERE n.nspname = 'public' AND p.proname = func_name
        LOOP
            EXECUTE 'DROP FUNCTION IF EXISTS ' || rec.func_sig || ' CASCADE';
        END LOOP;
    END LOOP;
END $$;

-- =====================================================
-- FUNGSI PEMBELIAN MULTI-ITEM (dengan invoice_number)
-- =====================================================
CREATE OR REPLACE FUNCTION record_purchase_transaction_multi(
    p_store TEXT,
    p_supplier_id INTEGER,
    p_warehouse_id INTEGER,
    p_items TEXT,
    p_payment_type TEXT,
    p_due_date TEXT DEFAULT NULL,
    p_account_id INTEGER DEFAULT NULL,
    p_description TEXT DEFAULT NULL,
    p_transaction_date TEXT DEFAULT NULL,
    p_created_by TEXT DEFAULT 'system',
    p_invoice_number TEXT DEFAULT NULL
)
RETURNS INTEGER AS $$
DECLARE
    v_transaction_id INTEGER;
    v_transaction_date TIMESTAMP;
    v_due_date TIMESTAMP;
    v_total_amount NUMERIC := 0;
    v_item JSONB;
    v_items JSONB;
    v_product_id INTEGER;
    v_quantity INTEGER;
    v_price NUMERIC;
    v_old_qty INTEGER;
    v_old_avg NUMERIC;
    v_new_avg NUMERIC;
    v_balance_after NUMERIC;
    v_supplier_name TEXT;
    v_description TEXT;
BEGIN
    IF p_transaction_date IS NOT NULL AND p_transaction_date != '' THEN
        v_transaction_date := p_transaction_date::TIMESTAMP;
    ELSE
        v_transaction_date := CURRENT_TIMESTAMP;
    END IF;
    
    IF p_due_date IS NOT NULL AND p_due_date != '' THEN
        v_due_date := p_due_date::TIMESTAMP;
    END IF;
    
    -- Get supplier name for description
    SELECT suppliername INTO v_supplier_name FROM supplier WHERE supplierid = p_supplier_id;
    
    v_items := p_items::JSONB;
    
    FOR v_item IN SELECT * FROM jsonb_array_elements(v_items)
    LOOP
        v_total_amount := v_total_amount + ((v_item->>'quantity')::INTEGER * (v_item->>'price')::NUMERIC);
    END LOOP;
    
    INSERT INTO purchase_transaction (
        store, supplier_id, warehouse_id, total_amount, payment_type, 
        due_date, account_id, description, transaction_date, created_by, invoice_number
    )
    VALUES (
        p_store, p_supplier_id, p_warehouse_id, v_total_amount, p_payment_type,
        v_due_date, p_account_id, p_description, v_transaction_date, p_created_by, p_invoice_number
    )
    RETURNING transaction_id INTO v_transaction_id;
    
    FOR v_item IN SELECT * FROM jsonb_array_elements(v_items)
    LOOP
        v_product_id := (v_item->>'product_id')::INTEGER;
        v_quantity := (v_item->>'quantity')::INTEGER;
        v_price := (v_item->>'price')::NUMERIC;
        
        INSERT INTO purchase_transaction_items (transaction_id, product_id, quantity, price)
        VALUES (v_transaction_id, v_product_id, v_quantity, v_price);
        
        INSERT INTO product_warehouse (productid, warehouseid, quantity)
        VALUES (v_product_id, p_warehouse_id, v_quantity)
        ON CONFLICT (productid, warehouseid) 
        DO UPDATE SET quantity = product_warehouse.quantity + v_quantity;
        
        SELECT COALESCE(quantity, 0), COALESCE(harga, 0)
        INTO v_old_qty, v_old_avg
        FROM product WHERE productid = v_product_id;
        
        IF (v_old_qty + v_quantity) > 0 THEN
            v_new_avg := ((v_old_qty * v_old_avg) + (v_quantity * v_price)) / (v_old_qty + v_quantity);
        ELSE
            v_new_avg := v_price;
        END IF;
        
        UPDATE product 
        SET quantity = quantity + v_quantity, harga = v_new_avg, updateat = CURRENT_TIMESTAMP
        WHERE productid = v_product_id;
        
        INSERT INTO productsupply (productid, supplierid, quantity, price, date)
        VALUES (v_product_id, p_supplier_id, v_quantity, v_price, v_transaction_date);
        
        -- Insert to purchase table for history
        INSERT INTO purchase (productid, supplierid, warehouseid, quantity, price, payment_type, description, date, invoice_number)
        VALUES (v_product_id, p_supplier_id, p_warehouse_id, v_quantity, v_price, p_payment_type, p_description, v_transaction_date, p_invoice_number);
    END LOOP;
    
    -- Build description for account transaction
    v_description := 'Pembelian dari ' || COALESCE(v_supplier_name, 'Supplier');
    IF p_invoice_number IS NOT NULL AND p_invoice_number != '' THEN
        v_description := v_description || ' (Nota: ' || p_invoice_number || ')';
    END IF;
    
    IF p_payment_type = 'cash' AND p_account_id IS NOT NULL THEN
        UPDATE accounts SET balance = balance - v_total_amount
        WHERE account_id = p_account_id
        RETURNING balance INTO v_balance_after;
        
        INSERT INTO account_transactions (
            account_id, transaction_type, related_id, amount, 
            balance_after, description, transaction_date, created_by
        )
        VALUES (
            p_account_id, 'purchase', v_transaction_id, -v_total_amount,
            v_balance_after, v_description, v_transaction_date, p_created_by
        );
    ELSIF p_payment_type = 'credit' THEN
        INSERT INTO debt (type, relatedid, amount, paid, date, description, store, due_date)
        VALUES ('supplier', p_supplier_id, v_total_amount, 0, v_transaction_date, v_description, p_store, v_due_date);
    END IF;
    
    RETURN v_transaction_id;
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- FUNGSI PENJUALAN MULTI-ITEM (dengan invoice_number)
-- =====================================================
CREATE OR REPLACE FUNCTION record_sale_transaction_multi(
    p_store TEXT,
    p_warehouse_id INTEGER,
    p_items TEXT,
    p_payment_type TEXT,
    p_customer_name TEXT DEFAULT NULL,
    p_due_date TEXT DEFAULT NULL,
    p_account_id INTEGER DEFAULT NULL,
    p_description TEXT DEFAULT NULL,
    p_transaction_date TEXT DEFAULT NULL,
    p_created_by TEXT DEFAULT 'system',
    p_invoice_number TEXT DEFAULT NULL
)
RETURNS INTEGER AS $$
DECLARE
    v_transaction_id INTEGER;
    v_transaction_date TIMESTAMP;
    v_due_date TIMESTAMP;
    v_total_amount NUMERIC := 0;
    v_item JSONB;
    v_items JSONB;
    v_product_id INTEGER;
    v_quantity INTEGER;
    v_price NUMERIC;
    v_balance_after NUMERIC;
    v_description TEXT;
BEGIN
    IF p_transaction_date IS NOT NULL AND p_transaction_date != '' THEN
        v_transaction_date := p_transaction_date::TIMESTAMP;
    ELSE
        v_transaction_date := CURRENT_TIMESTAMP;
    END IF;
    
    IF p_due_date IS NOT NULL AND p_due_date != '' THEN
        v_due_date := p_due_date::TIMESTAMP;
    END IF;
    
    v_items := p_items::JSONB;
    
    FOR v_item IN SELECT * FROM jsonb_array_elements(v_items)
    LOOP
        v_total_amount := v_total_amount + ((v_item->>'quantity')::INTEGER * (v_item->>'price')::NUMERIC);
    END LOOP;
    
    INSERT INTO sale_transaction (
        store, warehouse_id, customer_name, total_amount, payment_type, 
        due_date, account_id, description, transaction_date, created_by, invoice_number
    )
    VALUES (
        p_store, p_warehouse_id, p_customer_name, v_total_amount, p_payment_type,
        v_due_date, p_account_id, p_description, v_transaction_date, p_created_by, p_invoice_number
    )
    RETURNING transaction_id INTO v_transaction_id;
    
    FOR v_item IN SELECT * FROM jsonb_array_elements(v_items)
    LOOP
        v_product_id := (v_item->>'product_id')::INTEGER;
        v_quantity := (v_item->>'quantity')::INTEGER;
        v_price := (v_item->>'price')::NUMERIC;
        
        INSERT INTO sale_transaction_items (transaction_id, product_id, quantity, price)
        VALUES (v_transaction_id, v_product_id, v_quantity, v_price);
        
        UPDATE product_warehouse 
        SET quantity = quantity - v_quantity
        WHERE productid = v_product_id AND warehouseid = p_warehouse_id;
        
        UPDATE product 
        SET quantity = quantity - v_quantity, updateat = CURRENT_TIMESTAMP
        WHERE productid = v_product_id;
        
        -- Insert to sale table for history
        INSERT INTO sale (productid, warehouseid, customername, quantity, price, payment_type, description, date, invoice_number)
        VALUES (v_product_id, p_warehouse_id, p_customer_name, v_quantity, v_price, p_payment_type, p_description, v_transaction_date, p_invoice_number);
    END LOOP;
    
    -- Build description for account transaction
    v_description := 'Penjualan kepada ' || COALESCE(p_customer_name, 'Pelanggan');
    IF p_invoice_number IS NOT NULL AND p_invoice_number != '' THEN
        v_description := v_description || ' (Nota: ' || p_invoice_number || ')';
    END IF;
    
    IF p_payment_type = 'cash' AND p_account_id IS NOT NULL THEN
        UPDATE accounts SET balance = balance + v_total_amount
        WHERE account_id = p_account_id
        RETURNING balance INTO v_balance_after;
        
        INSERT INTO account_transactions (
            account_id, transaction_type, related_id, amount, 
            balance_after, description, transaction_date, created_by
        )
        VALUES (
            p_account_id, 'sale', v_transaction_id, v_total_amount,
            v_balance_after, v_description, v_transaction_date, p_created_by
        );
    ELSIF p_payment_type = 'credit' THEN
        INSERT INTO debt (type, relatedid, amount, paid, date, description, store, due_date)
        VALUES ('customer', v_transaction_id, v_total_amount, 0, v_transaction_date, v_description, p_store, v_due_date);
    END IF;
    
    RETURN v_transaction_id;
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- FUNGSI PEMBELIAN LAINNYA (NON-STOK)
-- =====================================================
CREATE OR REPLACE FUNCTION record_other_purchase(
    p_store TEXT,
    p_supplier_name TEXT,
    p_item_name TEXT,
    p_item_type TEXT,
    p_quantity INTEGER,
    p_price NUMERIC,
    p_payment_type TEXT,
    p_due_date TEXT DEFAULT NULL,
    p_account_id INTEGER DEFAULT NULL,
    p_description TEXT DEFAULT NULL,
    p_transaction_date TEXT DEFAULT NULL,
    p_created_by TEXT DEFAULT 'system',
    p_invoice_number TEXT DEFAULT NULL
)
RETURNS INTEGER AS $$
DECLARE
    v_transaction_id INTEGER;
    v_transaction_date TIMESTAMP;
    v_due_date TIMESTAMP;
    v_total_amount NUMERIC;
    v_balance_after NUMERIC;
    v_tx_description TEXT;
BEGIN
    IF p_transaction_date IS NOT NULL AND p_transaction_date != '' THEN
        v_transaction_date := p_transaction_date::TIMESTAMP;
    ELSE
        v_transaction_date := CURRENT_TIMESTAMP;
    END IF;
    
    IF p_due_date IS NOT NULL AND p_due_date != '' THEN
        v_due_date := p_due_date::TIMESTAMP;
    END IF;
    
    v_total_amount := p_quantity * p_price;
    
    -- Insert to purchase_transaction as non-stock
    INSERT INTO purchase_transaction (
        store, supplier_id, warehouse_id, total_amount, payment_type, 
        due_date, account_id, description, transaction_date, created_by, invoice_number, is_non_stock
    )
    VALUES (
        p_store, NULL, NULL, v_total_amount, p_payment_type,
        v_due_date, p_account_id, p_description, v_transaction_date, p_created_by, p_invoice_number, TRUE
    )
    RETURNING transaction_id INTO v_transaction_id;
    
    -- Insert to purchase table (non-stock)
    INSERT INTO purchase (productid, supplierid, warehouseid, quantity, price, payment_type, description, date, invoice_number, is_non_stock, item_name, item_type, store)
    VALUES (NULL, NULL, NULL, p_quantity, p_price, p_payment_type, p_description, v_transaction_date, p_invoice_number, TRUE, p_item_name, p_item_type, p_store);
    
    -- Build description for account transaction
    v_tx_description := 'Pembelian Lainnya: ' || p_item_name || ' dari ' || COALESCE(p_supplier_name, 'Supplier');
    IF p_invoice_number IS NOT NULL AND p_invoice_number != '' THEN
        v_tx_description := v_tx_description || ' (Nota: ' || p_invoice_number || ')';
    END IF;
    
    IF p_payment_type = 'cash' AND p_account_id IS NOT NULL THEN
        UPDATE accounts SET balance = balance - v_total_amount
        WHERE account_id = p_account_id
        RETURNING balance INTO v_balance_after;
        
        INSERT INTO account_transactions (
            account_id, transaction_type, related_id, amount, 
            balance_after, description, transaction_date, created_by
        )
        VALUES (
            p_account_id, 'other_purchase', v_transaction_id, -v_total_amount,
            v_balance_after, v_tx_description, v_transaction_date, p_created_by
        );
    ELSIF p_payment_type = 'credit' THEN
        INSERT INTO debt (type, relatedid, amount, paid, date, description, store, due_date)
        VALUES ('other_supplier', v_transaction_id, v_total_amount, 0, v_transaction_date, v_tx_description, p_store, v_due_date);
    END IF;
    
    RETURN v_transaction_id;
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- FUNGSI PENJUALAN LAINNYA (NON-STOK)
-- =====================================================
CREATE OR REPLACE FUNCTION record_other_sale(
    p_store TEXT,
    p_customer_name TEXT,
    p_item_name TEXT,
    p_item_type TEXT,
    p_quantity INTEGER,
    p_price NUMERIC,
    p_payment_type TEXT,
    p_due_date TEXT DEFAULT NULL,
    p_account_id INTEGER DEFAULT NULL,
    p_description TEXT DEFAULT NULL,
    p_transaction_date TEXT DEFAULT NULL,
    p_created_by TEXT DEFAULT 'system',
    p_invoice_number TEXT DEFAULT NULL
)
RETURNS INTEGER AS $$
DECLARE
    v_transaction_id INTEGER;
    v_transaction_date TIMESTAMP;
    v_due_date TIMESTAMP;
    v_total_amount NUMERIC;
    v_balance_after NUMERIC;
    v_tx_description TEXT;
BEGIN
    IF p_transaction_date IS NOT NULL AND p_transaction_date != '' THEN
        v_transaction_date := p_transaction_date::TIMESTAMP;
    ELSE
        v_transaction_date := CURRENT_TIMESTAMP;
    END IF;
    
    IF p_due_date IS NOT NULL AND p_due_date != '' THEN
        v_due_date := p_due_date::TIMESTAMP;
    END IF;
    
    v_total_amount := p_quantity * p_price;
    
    -- Insert to sale_transaction as non-stock
    INSERT INTO sale_transaction (
        store, warehouse_id, customer_name, total_amount, payment_type, 
        due_date, account_id, description, transaction_date, created_by, invoice_number, is_non_stock
    )
    VALUES (
        p_store, NULL, p_customer_name, v_total_amount, p_payment_type,
        v_due_date, p_account_id, p_description, v_transaction_date, p_created_by, p_invoice_number, TRUE
    )
    RETURNING transaction_id INTO v_transaction_id;
    
    -- Insert to sale table (non-stock)
    INSERT INTO sale (productid, warehouseid, customername, quantity, price, payment_type, description, date, invoice_number, is_non_stock, item_name, item_type, store)
    VALUES (NULL, NULL, p_customer_name, p_quantity, p_price, p_payment_type, p_description, v_transaction_date, p_invoice_number, TRUE, p_item_name, p_item_type, p_store);
    
    -- Build description for account transaction
    v_tx_description := 'Penjualan Lainnya: ' || p_item_name || ' kepada ' || COALESCE(p_customer_name, 'Pelanggan');
    IF p_invoice_number IS NOT NULL AND p_invoice_number != '' THEN
        v_tx_description := v_tx_description || ' (Nota: ' || p_invoice_number || ')';
    END IF;
    
    IF p_payment_type = 'cash' AND p_account_id IS NOT NULL THEN
        UPDATE accounts SET balance = balance + v_total_amount
        WHERE account_id = p_account_id
        RETURNING balance INTO v_balance_after;
        
        INSERT INTO account_transactions (
            account_id, transaction_type, related_id, amount, 
            balance_after, description, transaction_date, created_by
        )
        VALUES (
            p_account_id, 'other_sale', v_transaction_id, v_total_amount,
            v_balance_after, v_tx_description, v_transaction_date, p_created_by
        );
    ELSIF p_payment_type = 'credit' THEN
        INSERT INTO debt (type, relatedid, amount, paid, date, description, store, due_date)
        VALUES ('other_customer', v_transaction_id, v_total_amount, 0, v_transaction_date, v_tx_description, p_store, v_due_date);
    END IF;
    
    RETURN v_transaction_id;
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- FUNGSI GET PURCHASE HISTORY (dengan invoice_number dan non-stock)
-- =====================================================
CREATE OR REPLACE FUNCTION get_purchase_history(
    store_input TEXT,
    start_date_input TEXT,
    end_date_input TEXT
)
RETURNS TABLE (
    purchaseid INTEGER,
    product_name TEXT,
    supplier_name TEXT,
    warehouse_name TEXT,
    quantity INTEGER,
    price NUMERIC,
    total NUMERIC,
    payment_type TEXT,
    description TEXT,
    purchase_date TIMESTAMP,
    invoice_number TEXT,
    is_non_stock BOOLEAN
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        p.purchaseid,
        COALESCE(pr.productname, p.item_name, 'Item Non-Stok')::TEXT as product_name,
        COALESCE(s.suppliername, '-')::TEXT as supplier_name,
        COALESCE(w.name, '-')::TEXT as warehouse_name,
        p.quantity,
        p.price,
        (p.quantity * p.price) as total,
        p.payment_type::TEXT,
        p.description::TEXT,
        p.date as purchase_date,
        p.invoice_number::TEXT,
        COALESCE(p.is_non_stock, FALSE) as is_non_stock
    FROM purchase p
    LEFT JOIN product pr ON p.productid = pr.productid
    LEFT JOIN supplier s ON p.supplierid = s.supplierid
    LEFT JOIN warehouse_list w ON p.warehouseid = w.warehouseid
    WHERE (pr.store = store_input OR p.store = store_input)
      AND p.date >= start_date_input::TIMESTAMP
      AND p.date < end_date_input::TIMESTAMP
    ORDER BY p.date DESC;
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- FUNGSI GET SALE HISTORY (dengan invoice_number dan non-stock)
-- =====================================================
CREATE OR REPLACE FUNCTION get_sale_history(
    store_input TEXT,
    start_date_input TEXT,
    end_date_input TEXT
)
RETURNS TABLE (
    saleid INTEGER,
    product_name TEXT,
    warehouse_name TEXT,
    customer_name TEXT,
    quantity INTEGER,
    price NUMERIC,
    total NUMERIC,
    payment_type TEXT,
    description TEXT,
    sale_date TIMESTAMP,
    invoice_number TEXT,
    is_non_stock BOOLEAN
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        s.saleid,
        COALESCE(pr.productname, s.item_name, 'Item Non-Stok')::TEXT as product_name,
        COALESCE(w.name, '-')::TEXT as warehouse_name,
        COALESCE(s.customername, '-')::TEXT as customer_name,
        s.quantity,
        s.price,
        (s.quantity * s.price) as total,
        s.payment_type::TEXT,
        s.description::TEXT,
        s.date as sale_date,
        s.invoice_number::TEXT,
        COALESCE(s.is_non_stock, FALSE) as is_non_stock
    FROM sale s
    LEFT JOIN product pr ON s.productid = pr.productid
    LEFT JOIN warehouse_list w ON s.warehouseid = w.warehouseid
    WHERE (pr.store = store_input OR s.store = store_input)
      AND s.date >= start_date_input::TIMESTAMP
      AND s.date < end_date_input::TIMESTAMP
    ORDER BY s.date DESC;
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- VERIFIKASI
-- =====================================================
SELECT 'Migration V2 berhasil!' as status;

SELECT proname, pg_get_function_arguments(oid) as arguments
FROM pg_proc 
WHERE proname IN ('record_purchase_transaction_multi', 'record_sale_transaction_multi', 
                  'record_other_purchase', 'record_other_sale',
                  'get_purchase_history', 'get_sale_history')
AND pronamespace = 'public'::regnamespace
ORDER BY proname;
