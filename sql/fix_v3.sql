-- =====================================================
-- FIX V3: Perbaikan untuk errors dan perubahan fitur
-- 1. Fix column customer_name (bukan customername)
-- 2. Fix warehouse_id untuk non-stock sales (allow NULL)
-- 3. Fix productid untuk non-stock sales (allow NULL)
-- 4. Fix get_sale_history function
-- 5. Tambah arus kas untuk pembayaran utang/piutang
-- 6. Hapus record_other_purchase, update record_other_sale
-- =====================================================

-- =====================================================
-- 1. ALTER TABLE untuk allow NULL pada sale dan sale_transaction
-- =====================================================
ALTER TABLE sale_transaction ALTER COLUMN warehouse_id DROP NOT NULL;
ALTER TABLE sale ALTER COLUMN productid DROP NOT NULL;
ALTER TABLE sale ALTER COLUMN warehouseid DROP NOT NULL;

-- Drop foreign key constraints temporarily untuk allow NULL
ALTER TABLE sale DROP CONSTRAINT IF EXISTS sale_productid_fkey;
ALTER TABLE sale DROP CONSTRAINT IF EXISTS sale_warehouseid_fkey;

-- Re-add constraints with ON DELETE SET NULL (allow NULL values)
ALTER TABLE sale ADD CONSTRAINT sale_productid_fkey 
    FOREIGN KEY (productid) REFERENCES product(productid) ON DELETE SET NULL;
ALTER TABLE sale ADD CONSTRAINT sale_warehouseid_fkey 
    FOREIGN KEY (warehouseid) REFERENCES warehouse_list(warehouseid) ON DELETE SET NULL;

-- =====================================================
-- 2. DROP fungsi-fungsi yang akan diupdate
-- =====================================================
DO $$
DECLARE
    funcs TEXT[] := ARRAY[
        'record_sale_transaction_multi',
        'record_other_sale',
        'record_other_purchase',
        'get_sale_history',
        'record_supplier_payment',
        'record_customer_payment'
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
-- 3. FUNGSI PENJUALAN MULTI-ITEM (fix customer_name)
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
        
        -- Insert to sale table for history (use customer_name, NOT customername)
        INSERT INTO sale (productid, warehouseid, customer_name, quantity, price, payment_type, description, date, invoice_number)
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
-- 4. FUNGSI PENJUALAN LAINNYA (NON-STOK) - Langsung masuk laba
-- Tidak ada HPP, langsung tercatat sebagai pendapatan/laba
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
    
    -- Insert to sale_transaction as non-stock (warehouse_id can be NULL now)
    INSERT INTO sale_transaction (
        store, warehouse_id, customer_name, total_amount, payment_type, 
        due_date, account_id, description, transaction_date, created_by, invoice_number, is_non_stock
    )
    VALUES (
        p_store, NULL, p_customer_name, v_total_amount, p_payment_type,
        v_due_date, p_account_id, p_description, v_transaction_date, p_created_by, p_invoice_number, TRUE
    )
    RETURNING transaction_id INTO v_transaction_id;
    
    -- Insert to sale table (non-stock) using customer_name NOT customername
    INSERT INTO sale (productid, warehouseid, customer_name, quantity, price, payment_type, description, date, invoice_number, is_non_stock, item_name, item_type, store)
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
        VALUES ('customer', v_transaction_id, v_total_amount, 0, v_transaction_date, v_tx_description, p_store, v_due_date);
    END IF;
    
    RETURN v_transaction_id;
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- 5. FUNGSI GET SALE HISTORY (fix customer_name)
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
        COALESCE(s.customer_name, '-')::TEXT as customer_name,  -- FIXED: use customer_name
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
-- 6. FUNGSI PEMBAYARAN UTANG SUPPLIER (dengan arus kas dan No. Nota)
-- =====================================================
CREATE OR REPLACE FUNCTION record_supplier_payment(
    p_debtid INTEGER,
    p_amount NUMERIC,
    p_note TEXT DEFAULT NULL,
    p_transaction_date TEXT DEFAULT NULL,
    p_account_id INTEGER DEFAULT NULL
)
RETURNS VOID AS $$
DECLARE
    v_transaction_date TIMESTAMP;
    v_balance_after NUMERIC;
    v_debt_description TEXT;
    v_supplier_name TEXT;
    v_store TEXT;
    v_invoice_number TEXT;
    v_full_description TEXT;
BEGIN
    IF p_transaction_date IS NOT NULL AND p_transaction_date != '' THEN
        v_transaction_date := p_transaction_date::TIMESTAMP;
    ELSE
        v_transaction_date := CURRENT_TIMESTAMP;
    END IF;
    
    -- Get debt info for description (debt description already contains nota info)
    SELECT d.description, d.store INTO v_debt_description, v_store
    FROM debt d WHERE d.debtid = p_debtid;
    
    -- Try to get invoice number from purchase_transaction if this is supplier debt
    SELECT pt.invoice_number INTO v_invoice_number
    FROM debt d
    LEFT JOIN purchase_transaction pt ON d.relatedid = pt.transaction_id AND d.type = 'supplier'
    WHERE d.debtid = p_debtid;
    
    -- Build full description
    v_full_description := 'Pembayaran Utang Supplier';
    IF v_invoice_number IS NOT NULL AND v_invoice_number != '' THEN
        v_full_description := v_full_description || ' (Nota: ' || v_invoice_number || ')';
    ELSIF v_debt_description IS NOT NULL THEN
        v_full_description := v_full_description || ' - ' || v_debt_description;
    END IF;
    
    -- Update debt record
    UPDATE debt 
    SET paid = paid + p_amount
    WHERE debtid = p_debtid;
    
    -- Insert into payment_history
    INSERT INTO payment_history (debtid, paidamount, paidat, description)
    VALUES (p_debtid, p_amount, v_transaction_date, p_note);
    
    -- Record to arus kas (account_transactions) if account_id provided
    IF p_account_id IS NOT NULL THEN
        UPDATE accounts SET balance = balance - p_amount
        WHERE account_id = p_account_id
        RETURNING balance INTO v_balance_after;
        
        INSERT INTO account_transactions (
            account_id, transaction_type, related_id, amount, 
            balance_after, description, transaction_date, created_by
        )
        VALUES (
            p_account_id, 'debt_payment', p_debtid, -p_amount,
            v_balance_after, v_full_description,
            v_transaction_date, 'system'
        );
    END IF;
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- 7. FUNGSI PENERIMAAN PEMBAYARAN PIUTANG (dengan arus kas dan No. Nota)
-- =====================================================
CREATE OR REPLACE FUNCTION record_customer_payment(
    p_debtid INTEGER,
    p_amount NUMERIC,
    p_note TEXT DEFAULT NULL,
    p_transaction_date TEXT DEFAULT NULL,
    p_account_id INTEGER DEFAULT NULL
)
RETURNS VOID AS $$
DECLARE
    v_transaction_date TIMESTAMP;
    v_balance_after NUMERIC;
    v_debt_description TEXT;
    v_store TEXT;
    v_invoice_number TEXT;
    v_full_description TEXT;
BEGIN
    IF p_transaction_date IS NOT NULL AND p_transaction_date != '' THEN
        v_transaction_date := p_transaction_date::TIMESTAMP;
    ELSE
        v_transaction_date := CURRENT_TIMESTAMP;
    END IF;
    
    -- Get debt info for description (debt description already contains nota info)
    SELECT d.description, d.store INTO v_debt_description, v_store
    FROM debt d WHERE d.debtid = p_debtid;
    
    -- Try to get invoice number from sale_transaction if this is customer debt
    SELECT st.invoice_number INTO v_invoice_number
    FROM debt d
    LEFT JOIN sale_transaction st ON d.relatedid = st.transaction_id AND d.type = 'customer'
    WHERE d.debtid = p_debtid;
    
    -- Build full description
    v_full_description := 'Penerimaan Piutang Pelanggan';
    IF v_invoice_number IS NOT NULL AND v_invoice_number != '' THEN
        v_full_description := v_full_description || ' (Nota: ' || v_invoice_number || ')';
    ELSIF v_debt_description IS NOT NULL THEN
        v_full_description := v_full_description || ' - ' || v_debt_description;
    END IF;
    
    -- Update debt record
    UPDATE debt 
    SET paid = paid + p_amount
    WHERE debtid = p_debtid;
    
    -- Insert into payment_history
    INSERT INTO payment_history (debtid, paidamount, paidat, description)
    VALUES (p_debtid, p_amount, v_transaction_date, p_note);
    
    -- Record to arus kas (account_transactions) if account_id provided
    IF p_account_id IS NOT NULL THEN
        UPDATE accounts SET balance = balance + p_amount
        WHERE account_id = p_account_id
        RETURNING balance INTO v_balance_after;
        
        INSERT INTO account_transactions (
            account_id, transaction_type, related_id, amount, 
            balance_after, description, transaction_date, created_by
        )
        VALUES (
            p_account_id, 'receivable_payment', p_debtid, p_amount,
            v_balance_after, v_full_description,
            v_transaction_date, 'system'
        );
    END IF;
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- VERIFIKASI
-- =====================================================
SELECT 'Fix V3 berhasil!' as status;

SELECT proname, pg_get_function_arguments(oid) as arguments
FROM pg_proc 
WHERE proname IN ('record_sale_transaction_multi', 'record_other_sale', 
                  'get_sale_history', 'record_supplier_payment', 'record_customer_payment')
AND pronamespace = 'public'::regnamespace
ORDER BY proname;
