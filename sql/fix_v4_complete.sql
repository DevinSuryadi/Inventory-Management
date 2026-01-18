-- =====================================================
-- FIX V4 COMPLETE: Integrasi LENGKAP semua transaksi dengan Arus Kas
-- =====================================================
-- Transaksi yang terintegrasi:
-- 1. Pembelian (record_purchase_transaction_multi)
-- 2. Penjualan Biasa (record_sale_transaction_multi)
-- 3. Penjualan Lainnya Non-Stok (record_other_sale)
-- 4. Retur Pembelian (record_purchase_return)
-- 5. Retur Penjualan (record_sale_return)
-- 6. Pembayaran Utang Supplier (record_supplier_payment)
-- 7. Penerimaan Piutang Pelanggan (record_customer_payment)
-- 8. Biaya Operasional (record_operational_expense)
-- 9. Pembayaran Gaji Pegawai (record_pegawai_payment) -> masuk ke biaya operasional
-- 10. Penyesuaian Saldo (adjust_account_balance)
-- 11. Transfer Dana (transfer_funds)
-- =====================================================

-- =====================================================
-- STEP 1: ALTER TABLE untuk allow NULL pada sale dan sale_transaction
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

-- Tambah kolom invoice_number ke purchase_return jika belum ada
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'purchase_return' AND column_name = 'invoice_number') THEN
        ALTER TABLE purchase_return ADD COLUMN invoice_number VARCHAR(100);
    END IF;
END $$;

-- Tambah kolom invoice_number ke sale_return jika belum ada
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'sale_return' AND column_name = 'invoice_number') THEN
        ALTER TABLE sale_return ADD COLUMN invoice_number VARCHAR(100);
    END IF;
END $$;

-- Tambah kolom invoice_number ke purchase jika belum ada
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'purchase' AND column_name = 'invoice_number') THEN
        ALTER TABLE purchase ADD COLUMN invoice_number VARCHAR(100);
    END IF;
END $$;

-- Tambah kolom store ke purchase jika belum ada
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'purchase' AND column_name = 'store') THEN
        ALTER TABLE purchase ADD COLUMN store VARCHAR(100);
    END IF;
END $$;

-- =====================================================
-- FUNGSI GET SUPPLIER DEBT TOTAL
-- Menghitung total utang ke supplier tertentu
-- =====================================================
CREATE OR REPLACE FUNCTION get_supplier_debt_total(
    p_store TEXT,
    p_supplier_id INTEGER DEFAULT NULL
)
RETURNS NUMERIC AS $$
DECLARE
    v_total NUMERIC := 0;
BEGIN
    IF p_supplier_id IS NOT NULL THEN
        -- Get total debt for specific supplier
        SELECT COALESCE(SUM(amount - paid), 0) INTO v_total
        FROM debt
        WHERE type = 'supplier'
          AND store = p_store
          AND relatedid IN (
              SELECT transaction_id FROM purchase_transaction 
              WHERE supplier_id = p_supplier_id AND store = p_store
          )
          AND (amount - paid) > 0;
    ELSE
        -- Get total debt for all suppliers in store
        SELECT COALESCE(SUM(amount - paid), 0) INTO v_total
        FROM debt
        WHERE type = 'supplier'
          AND store = p_store
          AND (amount - paid) > 0;
    END IF;
    
    RETURN v_total;
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- STEP 2: DROP semua fungsi yang akan diupdate
-- =====================================================
DO $$
DECLARE
    funcs TEXT[] := ARRAY[
        'record_purchase_transaction_multi',
        'record_sale_transaction_multi',
        'record_other_sale',
        'record_purchase_return',
        'record_sale_return',
        'record_supplier_payment',
        'record_customer_payment',
        'record_operational_expense',
        'record_pegawai_payment',
        'adjust_account_balance',
        'transfer_funds',
        'get_sale_history',
        'get_supplier_debt_total',
        'get_purchase_return_history',
        'get_sale_return_history'
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
-- 1. FUNGSI PEMBELIAN MULTI-ITEM (dengan invoice_number dan arus kas)
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
    
    v_items := p_items::JSONB;
    
    -- Get supplier name
    SELECT suppliername INTO v_supplier_name FROM supplier WHERE supplierid = p_supplier_id;
    
    -- Calculate total
    FOR v_item IN SELECT * FROM jsonb_array_elements(v_items)
    LOOP
        v_total_amount := v_total_amount + ((v_item->>'quantity')::INTEGER * (v_item->>'price')::NUMERIC);
    END LOOP;
    
    -- Insert transaction header
    INSERT INTO purchase_transaction (
        store, supplier_id, warehouse_id, total_amount, payment_type, 
        due_date, account_id, description, transaction_date, created_by, invoice_number
    )
    VALUES (
        p_store, p_supplier_id, p_warehouse_id, v_total_amount, p_payment_type,
        v_due_date, p_account_id, p_description, v_transaction_date, p_created_by, p_invoice_number
    )
    RETURNING transaction_id INTO v_transaction_id;
    
    -- Process each item
    FOR v_item IN SELECT * FROM jsonb_array_elements(v_items)
    LOOP
        v_product_id := (v_item->>'product_id')::INTEGER;
        v_quantity := (v_item->>'quantity')::INTEGER;
        v_price := (v_item->>'price')::NUMERIC;
        
        -- Insert transaction item
        INSERT INTO purchase_transaction_items (transaction_id, product_id, quantity, price)
        VALUES (v_transaction_id, v_product_id, v_quantity, v_price);
        
        -- Update/Insert stock di warehouse
        INSERT INTO product_warehouse (productid, warehouseid, quantity)
        VALUES (v_product_id, p_warehouse_id, v_quantity)
        ON CONFLICT (productid, warehouseid) 
        DO UPDATE SET quantity = product_warehouse.quantity + v_quantity;
        
        -- Get current stock and average price for weighted average calculation
        SELECT COALESCE(quantity, 0), COALESCE(harga, 0)
        INTO v_old_qty, v_old_avg
        FROM product
        WHERE productid = v_product_id;
        
        -- Calculate new weighted average price
        IF (v_old_qty + v_quantity) > 0 THEN
            v_new_avg := ((v_old_qty * v_old_avg) + (v_quantity * v_price)) / (v_old_qty + v_quantity);
        ELSE
            v_new_avg := v_price;
        END IF;
        
        -- Update product total quantity and average price (harga)
        UPDATE product 
        SET quantity = quantity + v_quantity,
            harga = v_new_avg,
            updateat = CURRENT_TIMESTAMP
        WHERE productid = v_product_id;
        
        -- Insert productsupply record for price tracking per supplier
        INSERT INTO productsupply (productid, supplierid, quantity, price, date)
        VALUES (v_product_id, p_supplier_id, v_quantity, v_price, v_transaction_date);
        
        -- Insert to purchase table for history (like sale table does)
        INSERT INTO purchase (productid, supplierid, warehouseid, quantity, price, payment_type, description, date, invoice_number, store)
        VALUES (v_product_id, p_supplier_id, p_warehouse_id, v_quantity, v_price, p_payment_type, p_description, v_transaction_date, p_invoice_number, p_store);
    END LOOP;
    
    -- Build description for arus kas
    v_tx_description := 'Pembelian dari ' || COALESCE(v_supplier_name, 'Supplier');
    IF p_invoice_number IS NOT NULL AND p_invoice_number != '' THEN
        v_tx_description := v_tx_description || ' (Nota: ' || p_invoice_number || ')';
    END IF;
    
    -- Handle payment
    IF p_payment_type = 'cash' AND p_account_id IS NOT NULL THEN
        -- Deduct from account
        UPDATE accounts 
        SET balance = balance - v_total_amount
        WHERE account_id = p_account_id
        RETURNING balance INTO v_balance_after;
        
        INSERT INTO account_transactions (
            account_id, transaction_type, related_id, amount, 
            balance_after, description, transaction_date, created_by
        )
        VALUES (
            p_account_id, 'purchase', v_transaction_id, -v_total_amount,
            v_balance_after, v_tx_description, 
            v_transaction_date, p_created_by
        );
    ELSIF p_payment_type = 'credit' THEN
        -- Create debt (hutang ke supplier)
        INSERT INTO debt (type, relatedid, amount, paid, date, description, store, due_date)
        VALUES ('supplier', v_transaction_id, v_total_amount, 0, v_transaction_date, v_tx_description, p_store, v_due_date);
    END IF;
    
    RETURN v_transaction_id;
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- 2. FUNGSI PENJUALAN MULTI-ITEM (dengan invoice_number dan arus kas)
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
    
    -- Build description for arus kas
    v_tx_description := 'Penjualan kepada ' || COALESCE(p_customer_name, 'Pelanggan');
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
            p_account_id, 'sale', v_transaction_id, v_total_amount,
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
-- 3. FUNGSI PENJUALAN LAINNYA NON-STOK (langsung masuk laba)
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
    
    -- Build description for arus kas
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
-- 4. FUNGSI RETUR PEMBELIAN (dengan arus kas)
-- =====================================================
CREATE OR REPLACE FUNCTION record_purchase_return(
    p_store TEXT,
    p_supplier_id INTEGER,
    p_warehouse_id INTEGER,
    p_items TEXT,
    p_return_type TEXT,
    p_reason TEXT DEFAULT NULL,
    p_description TEXT DEFAULT NULL,
    p_account_id INTEGER DEFAULT NULL,
    p_return_date TEXT DEFAULT NULL,
    p_created_by TEXT DEFAULT 'system',
    p_invoice_number TEXT DEFAULT NULL
)
RETURNS INTEGER AS $$
DECLARE
    v_return_id INTEGER;
    v_return_date TIMESTAMP;
    v_total_amount NUMERIC := 0;
    v_item JSONB;
    v_items JSONB;
    v_balance_after NUMERIC;
    v_supplier_name TEXT;
    v_tx_description TEXT;
BEGIN
    IF p_return_date IS NOT NULL AND p_return_date != '' THEN
        v_return_date := p_return_date::TIMESTAMP;
    ELSE
        v_return_date := CURRENT_TIMESTAMP;
    END IF;
    
    v_items := p_items::JSONB;
    
    -- Get supplier name
    SELECT suppliername INTO v_supplier_name FROM supplier WHERE supplierid = p_supplier_id;
    
    -- Calculate total
    FOR v_item IN SELECT * FROM jsonb_array_elements(v_items)
    LOOP
        v_total_amount := v_total_amount + ((v_item->>'quantity')::INTEGER * (v_item->>'price')::NUMERIC);
    END LOOP;
    
    -- Insert return header
    INSERT INTO purchase_return (
        store, supplier_id, warehouse_id, total_amount, return_type,
        status, reason, description, account_id, return_date, created_by, invoice_number
    )
    VALUES (
        p_store, p_supplier_id, p_warehouse_id, v_total_amount, p_return_type,
        'completed', p_reason, p_description, p_account_id, v_return_date, p_created_by, p_invoice_number
    )
    RETURNING return_id INTO v_return_id;
    
    -- Insert items and update stock
    FOR v_item IN SELECT * FROM jsonb_array_elements(v_items)
    LOOP
        -- Insert return item
        INSERT INTO purchase_return_items (return_id, product_id, quantity, price)
        VALUES (
            v_return_id,
            (v_item->>'product_id')::INTEGER,
            (v_item->>'quantity')::INTEGER,
            (v_item->>'price')::NUMERIC
        );
        
        -- Reduce stock from warehouse (barang dikembalikan ke supplier)
        UPDATE product_warehouse 
        SET quantity = quantity - (v_item->>'quantity')::INTEGER
        WHERE productid = (v_item->>'product_id')::INTEGER 
          AND warehouseid = p_warehouse_id;
        
        -- Update product total quantity
        UPDATE product 
        SET quantity = quantity - (v_item->>'quantity')::INTEGER,
            updateat = CURRENT_TIMESTAMP
        WHERE productid = (v_item->>'product_id')::INTEGER;
    END LOOP;
    
    -- Build description for arus kas
    v_tx_description := 'Retur Pembelian ke ' || COALESCE(v_supplier_name, 'Supplier');
    IF p_invoice_number IS NOT NULL AND p_invoice_number != '' THEN
        v_tx_description := v_tx_description || ' (Nota: ' || p_invoice_number || ')';
    END IF;
    
    -- Handle based on return type
    IF p_return_type = 'credit_note' THEN
        -- Potong hutang ke supplier
        UPDATE debt 
        SET paid = paid + v_total_amount
        WHERE debtid = (
            SELECT debtid FROM debt 
            WHERE type = 'supplier' 
              AND store = p_store 
              AND relatedid = p_supplier_id
              AND (amount - paid) > 0
            ORDER BY date ASC
            LIMIT 1
        );
    ELSIF p_return_type = 'refund' AND p_account_id IS NOT NULL THEN
        -- Terima refund ke rekening
        UPDATE accounts 
        SET balance = balance + v_total_amount
        WHERE account_id = p_account_id
        RETURNING balance INTO v_balance_after;
        
        INSERT INTO account_transactions (
            account_id, transaction_type, related_id, amount, 
            balance_after, description, transaction_date, created_by
        )
        VALUES (
            p_account_id, 'purchase_return', v_return_id, v_total_amount,
            v_balance_after, v_tx_description, 
            v_return_date, p_created_by
        );
    END IF;
    
    RETURN v_return_id;
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- 5. FUNGSI RETUR PENJUALAN (dengan arus kas)
-- =====================================================
CREATE OR REPLACE FUNCTION record_sale_return(
    p_store TEXT,
    p_warehouse_id INTEGER,
    p_customer_name TEXT,
    p_items TEXT,
    p_return_type TEXT,
    p_reason TEXT DEFAULT NULL,
    p_description TEXT DEFAULT NULL,
    p_account_id INTEGER DEFAULT NULL,
    p_return_date TEXT DEFAULT NULL,
    p_created_by TEXT DEFAULT 'system',
    p_invoice_number TEXT DEFAULT NULL
)
RETURNS INTEGER AS $$
DECLARE
    v_return_id INTEGER;
    v_return_date TIMESTAMP;
    v_total_amount NUMERIC := 0;
    v_item JSONB;
    v_items JSONB;
    v_balance_after NUMERIC;
    v_tx_description TEXT;
BEGIN
    IF p_return_date IS NOT NULL AND p_return_date != '' THEN
        v_return_date := p_return_date::TIMESTAMP;
    ELSE
        v_return_date := CURRENT_TIMESTAMP;
    END IF;
    
    v_items := p_items::JSONB;
    
    -- Calculate total
    FOR v_item IN SELECT * FROM jsonb_array_elements(v_items)
    LOOP
        v_total_amount := v_total_amount + ((v_item->>'quantity')::INTEGER * (v_item->>'price')::NUMERIC);
    END LOOP;
    
    -- Insert return header
    INSERT INTO sale_return (
        store, customer_name, warehouse_id, total_amount, return_type,
        status, reason, description, account_id, return_date, created_by, invoice_number
    )
    VALUES (
        p_store, p_customer_name, p_warehouse_id, v_total_amount, p_return_type,
        'completed', p_reason, p_description, p_account_id, v_return_date, p_created_by, p_invoice_number
    )
    RETURNING return_id INTO v_return_id;
    
    -- Insert items and update stock
    FOR v_item IN SELECT * FROM jsonb_array_elements(v_items)
    LOOP
        -- Insert return item
        INSERT INTO sale_return_items (return_id, product_id, quantity, price)
        VALUES (
            v_return_id,
            (v_item->>'product_id')::INTEGER,
            (v_item->>'quantity')::INTEGER,
            (v_item->>'price')::NUMERIC
        );
        
        -- Add stock back to warehouse (barang kembali dari pelanggan)
        INSERT INTO product_warehouse (productid, warehouseid, quantity)
        VALUES ((v_item->>'product_id')::INTEGER, p_warehouse_id, (v_item->>'quantity')::INTEGER)
        ON CONFLICT (productid, warehouseid) 
        DO UPDATE SET quantity = product_warehouse.quantity + (v_item->>'quantity')::INTEGER;
        
        -- Update product total quantity
        UPDATE product 
        SET quantity = quantity + (v_item->>'quantity')::INTEGER,
            updateat = CURRENT_TIMESTAMP
        WHERE productid = (v_item->>'product_id')::INTEGER;
    END LOOP;
    
    -- Build description for arus kas
    v_tx_description := 'Retur Penjualan dari ' || COALESCE(p_customer_name, 'Pelanggan');
    IF p_invoice_number IS NOT NULL AND p_invoice_number != '' THEN
        v_tx_description := v_tx_description || ' (Nota: ' || p_invoice_number || ')';
    END IF;
    
    -- Handle based on return type
    IF p_return_type = 'refund' AND p_account_id IS NOT NULL THEN
        -- Bayar refund ke pelanggan (kurangi saldo)
        UPDATE accounts 
        SET balance = balance - v_total_amount
        WHERE account_id = p_account_id
        RETURNING balance INTO v_balance_after;
        
        INSERT INTO account_transactions (
            account_id, transaction_type, related_id, amount, 
            balance_after, description, transaction_date, created_by
        )
        VALUES (
            p_account_id, 'sale_return', v_return_id, -v_total_amount,
            v_balance_after, v_tx_description, 
            v_return_date, p_created_by
        );
    ELSIF p_return_type = 'credit_note' THEN
        -- Potong piutang dari customer
        UPDATE debt 
        SET paid = paid + v_total_amount
        WHERE debtid = (
            SELECT debtid FROM debt 
            WHERE type = 'customer' 
              AND store = p_store 
              AND (amount - paid) > 0
            ORDER BY date ASC
            LIMIT 1
        );
    END IF;
    
    RETURN v_return_id;
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
-- 8. FUNGSI BIAYA OPERASIONAL (dengan arus kas)
-- =====================================================
CREATE OR REPLACE FUNCTION record_operational_expense(
    p_store TEXT,
    p_expense_type TEXT,
    p_amount NUMERIC,
    p_description TEXT DEFAULT NULL,
    p_reference_id INTEGER DEFAULT NULL,
    p_account_id INTEGER DEFAULT NULL,
    p_expense_date TEXT DEFAULT NULL,
    p_created_by TEXT DEFAULT 'system'
)
RETURNS INTEGER AS $$
DECLARE
    v_expense_id INTEGER;
    v_expense_date TIMESTAMP;
    v_balance_after NUMERIC;
    v_tx_description TEXT;
BEGIN
    IF p_expense_date IS NOT NULL AND p_expense_date != '' THEN
        v_expense_date := p_expense_date::TIMESTAMP;
    ELSE
        v_expense_date := CURRENT_TIMESTAMP;
    END IF;
    
    -- Insert expense record
    INSERT INTO operational_expense (
        store, expense_type, amount, description, reference_id, 
        account_id, expense_date, created_by
    )
    VALUES (
        p_store, p_expense_type, p_amount, p_description, p_reference_id,
        p_account_id, v_expense_date, p_created_by
    )
    RETURNING expense_id INTO v_expense_id;
    
    -- Build description for arus kas
    v_tx_description := 'Biaya Operasional: ' || p_expense_type;
    IF p_description IS NOT NULL AND p_description != '' THEN
        v_tx_description := v_tx_description || ' - ' || p_description;
    END IF;
    
    -- Update account balance and record transaction if account provided
    IF p_account_id IS NOT NULL THEN
        UPDATE accounts 
        SET balance = balance - p_amount
        WHERE account_id = p_account_id
        RETURNING balance INTO v_balance_after;
        
        INSERT INTO account_transactions (
            account_id, transaction_type, related_id, amount, 
            balance_after, description, transaction_date, created_by
        )
        VALUES (
            p_account_id, 'expense', v_expense_id, -p_amount,
            v_balance_after, v_tx_description, 
            v_expense_date, p_created_by
        );
    END IF;
    
    RETURN v_expense_id;
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- 9. FUNGSI PEMBAYARAN GAJI PEGAWAI (dengan arus kas)
-- Menggunakan tabel pegawai_payment dan operational_expense
-- =====================================================
CREATE OR REPLACE FUNCTION record_pegawai_payment(
    p_store TEXT,
    p_pegawai_id INTEGER,
    p_bulan DATE,
    p_jumlah NUMERIC,
    p_account_id INTEGER DEFAULT NULL,
    p_description TEXT DEFAULT NULL,
    p_created_by TEXT DEFAULT 'system'
)
RETURNS INTEGER AS $$
DECLARE
    v_payment_id INTEGER;
    v_expense_id INTEGER;
    v_balance_after NUMERIC;
    v_pegawai_nama TEXT;
    v_tx_description TEXT;
BEGIN
    -- Get pegawai name
    SELECT nama INTO v_pegawai_nama FROM pegawai WHERE pegawai_id = p_pegawai_id;
    
    -- Insert to pegawai_payment
    INSERT INTO pegawai_payment (pegawai_id, bulan, jumlah, paid_at, status)
    VALUES (p_pegawai_id, p_bulan, p_jumlah, CURRENT_TIMESTAMP, 'paid')
    RETURNING payment_id INTO v_payment_id;
    
    -- Build description for arus kas
    v_tx_description := 'Pembayaran Gaji: ' || COALESCE(v_pegawai_nama, 'Pegawai');
    IF p_description IS NOT NULL AND p_description != '' THEN
        v_tx_description := v_tx_description || ' - ' || p_description;
    END IF;
    
    -- Insert to operational_expense as 'gaji'
    INSERT INTO operational_expense (
        store, expense_type, amount, description, reference_id, 
        account_id, expense_date, created_by
    )
    VALUES (
        p_store, 'gaji', p_jumlah, v_tx_description, p_pegawai_id,
        p_account_id, CURRENT_TIMESTAMP, p_created_by
    )
    RETURNING expense_id INTO v_expense_id;
    
    -- Update account balance and record transaction if account provided
    IF p_account_id IS NOT NULL THEN
        UPDATE accounts 
        SET balance = balance - p_jumlah
        WHERE account_id = p_account_id
        RETURNING balance INTO v_balance_after;
        
        INSERT INTO account_transactions (
            account_id, transaction_type, related_id, amount, 
            balance_after, description, transaction_date, created_by
        )
        VALUES (
            p_account_id, 'expense', v_expense_id, -p_jumlah,
            v_balance_after, v_tx_description, 
            CURRENT_TIMESTAMP, p_created_by
        );
    END IF;
    
    RETURN v_payment_id;
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- 10. FUNGSI PENYESUAIAN SALDO (dengan arus kas)
-- =====================================================
CREATE OR REPLACE FUNCTION adjust_account_balance(
    p_account_id INTEGER,
    p_amount NUMERIC,
    p_adjustment_type TEXT,
    p_description TEXT DEFAULT NULL,
    p_created_by TEXT DEFAULT 'system'
)
RETURNS VOID AS $$
DECLARE
    v_balance_after NUMERIC;
    v_tx_description TEXT;
BEGIN
    -- Build description
    IF p_adjustment_type = 'increase' THEN
        v_tx_description := 'Penyesuaian Saldo: Penambahan';
    ELSE
        v_tx_description := 'Penyesuaian Saldo: Pengurangan';
    END IF;
    
    IF p_description IS NOT NULL AND p_description != '' THEN
        v_tx_description := v_tx_description || ' - ' || p_description;
    END IF;
    
    IF p_adjustment_type = 'increase' THEN
        UPDATE accounts SET balance = balance + p_amount
        WHERE account_id = p_account_id
        RETURNING balance INTO v_balance_after;
        
        INSERT INTO account_transactions (
            account_id, transaction_type, amount, 
            balance_after, description, transaction_date, created_by
        )
        VALUES (
            p_account_id, 'adjustment', p_amount,
            v_balance_after, v_tx_description, CURRENT_TIMESTAMP, p_created_by
        );
    ELSE
        UPDATE accounts SET balance = balance - p_amount
        WHERE account_id = p_account_id
        RETURNING balance INTO v_balance_after;
        
        INSERT INTO account_transactions (
            account_id, transaction_type, amount, 
            balance_after, description, transaction_date, created_by
        )
        VALUES (
            p_account_id, 'adjustment', -p_amount,
            v_balance_after, v_tx_description, CURRENT_TIMESTAMP, p_created_by
        );
    END IF;
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- 11. FUNGSI TRANSFER DANA (dengan arus kas)
-- =====================================================
CREATE OR REPLACE FUNCTION transfer_funds(
    p_from_account_id INTEGER,
    p_to_account_id INTEGER,
    p_amount NUMERIC,
    p_description TEXT DEFAULT NULL,
    p_created_by TEXT DEFAULT 'system'
)
RETURNS VOID AS $$
DECLARE
    v_from_balance NUMERIC;
    v_to_balance NUMERIC;
    v_from_name TEXT;
    v_to_name TEXT;
    v_tx_description_from TEXT;
    v_tx_description_to TEXT;
BEGIN
    -- Get account names
    SELECT account_name INTO v_from_name FROM accounts WHERE account_id = p_from_account_id;
    SELECT account_name INTO v_to_name FROM accounts WHERE account_id = p_to_account_id;
    
    -- Build descriptions
    v_tx_description_from := 'Transfer ke ' || COALESCE(v_to_name, 'Rekening');
    v_tx_description_to := 'Transfer dari ' || COALESCE(v_from_name, 'Rekening');
    
    IF p_description IS NOT NULL AND p_description != '' THEN
        v_tx_description_from := v_tx_description_from || ' - ' || p_description;
        v_tx_description_to := v_tx_description_to || ' - ' || p_description;
    END IF;
    
    -- Deduct from source account
    UPDATE accounts SET balance = balance - p_amount
    WHERE account_id = p_from_account_id
    RETURNING balance INTO v_from_balance;
    
    -- Record outgoing transfer
    INSERT INTO account_transactions (
        account_id, transaction_type, amount, 
        balance_after, description, transaction_date, created_by
    )
    VALUES (
        p_from_account_id, 'transfer_out', -p_amount,
        v_from_balance, v_tx_description_from, CURRENT_TIMESTAMP, p_created_by
    );
    
    -- Add to destination account
    UPDATE accounts SET balance = balance + p_amount
    WHERE account_id = p_to_account_id
    RETURNING balance INTO v_to_balance;
    
    -- Record incoming transfer
    INSERT INTO account_transactions (
        account_id, transaction_type, amount, 
        balance_after, description, transaction_date, created_by
    )
    VALUES (
        p_to_account_id, 'transfer_in', p_amount,
        v_to_balance, v_tx_description_to, CURRENT_TIMESTAMP, p_created_by
    );
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- 12. FUNGSI GET SALE HISTORY (fix customer_name)
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
        COALESCE(s.customer_name, '-')::TEXT as customer_name,
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
-- 14. FUNGSI GET PURCHASE RETURN HISTORY
-- =====================================================
CREATE OR REPLACE FUNCTION get_purchase_return_history(
    store_input TEXT,
    start_date_input TEXT,
    end_date_input TEXT
)
RETURNS TABLE (
    return_id INTEGER,
    supplier_name TEXT,
    warehouse_name TEXT,
    total_amount NUMERIC,
    return_type TEXT,
    status TEXT,
    reason TEXT,
    return_date TIMESTAMP,
    item_count BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        pr.return_id,
        COALESCE(s.suppliername, '-')::TEXT as supplier_name,
        COALESCE(w.name, '-')::TEXT as warehouse_name,
        pr.total_amount,
        pr.return_type::TEXT,
        pr.status::TEXT,
        pr.reason::TEXT,
        pr.return_date,
        (SELECT COALESCE(SUM(pri.quantity), 0) FROM purchase_return_items pri WHERE pri.return_id = pr.return_id) as item_count
    FROM purchase_return pr
    LEFT JOIN supplier s ON pr.supplier_id = s.supplierid
    LEFT JOIN warehouse_list w ON pr.warehouse_id = w.warehouseid
    WHERE pr.store = store_input
      AND pr.return_date >= start_date_input::TIMESTAMP
      AND pr.return_date < end_date_input::TIMESTAMP
    ORDER BY pr.return_date DESC;
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- 15. FUNGSI GET SALE RETURN HISTORY
-- =====================================================
CREATE OR REPLACE FUNCTION get_sale_return_history(
    store_input TEXT,
    start_date_input TEXT,
    end_date_input TEXT
)
RETURNS TABLE (
    return_id INTEGER,
    customer_name TEXT,
    warehouse_name TEXT,
    total_amount NUMERIC,
    return_type TEXT,
    status TEXT,
    reason TEXT,
    return_date TIMESTAMP,
    item_count BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        sr.return_id,
        COALESCE(sr.customer_name, '-')::TEXT as customer_name,
        COALESCE(w.name, '-')::TEXT as warehouse_name,
        sr.total_amount,
        sr.return_type::TEXT,
        sr.status::TEXT,
        sr.reason::TEXT,
        sr.return_date,
        (SELECT COALESCE(SUM(sri.quantity), 0) FROM sale_return_items sri WHERE sri.return_id = sr.return_id) as item_count
    FROM sale_return sr
    LEFT JOIN warehouse_list w ON sr.warehouse_id = w.warehouseid
    WHERE sr.store = store_input
      AND sr.return_date >= start_date_input::TIMESTAMP
      AND sr.return_date < end_date_input::TIMESTAMP
    ORDER BY sr.return_date DESC;
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- VERIFIKASI
-- =====================================================
SELECT 'Fix V4 Complete berhasil dijalankan!' as status;

SELECT proname, pg_get_function_arguments(oid) as arguments
FROM pg_proc 
WHERE proname IN (
    'record_purchase_transaction_multi', 
    'record_sale_transaction_multi', 
    'record_other_sale',
    'record_purchase_return',
    'record_sale_return',
    'record_supplier_payment', 
    'record_customer_payment',
    'record_operational_expense',
    'record_pegawai_payment',
    'adjust_account_balance',
    'transfer_funds',
    'get_sale_history',
    'get_supplier_debt_total',
    'get_purchase_return_history',
    'get_sale_return_history'
)
AND pronamespace = 'public'::regnamespace
ORDER BY proname;
