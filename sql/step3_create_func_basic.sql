-- =====================================================
-- FILE 3: CREATE FUNCTION - STOK, PEMBAYARAN, EXPENSE
-- (JALANKAN KETIGA)
-- =====================================================

-- FUNGSI PENYESUAIAN STOK
CREATE OR REPLACE FUNCTION record_stock_adjustment(
    p_product_id INTEGER,
    p_warehouse_id INTEGER,
    p_adj_type TEXT,
    p_quantity INTEGER,
    p_description TEXT DEFAULT NULL,
    p_transaction_date TEXT DEFAULT NULL,
    p_price NUMERIC DEFAULT NULL,
    p_store TEXT DEFAULT NULL
)
RETURNS VOID AS $$
DECLARE
    v_transaction_date TIMESTAMP;
    v_store TEXT;
    v_price NUMERIC;
BEGIN
    IF p_transaction_date IS NOT NULL AND p_transaction_date != '' THEN
        v_transaction_date := p_transaction_date::TIMESTAMP;
    ELSE
        v_transaction_date := CURRENT_TIMESTAMP;
    END IF;
    
    IF p_store IS NULL OR p_store = '' THEN
        SELECT store INTO v_store FROM product WHERE productid = p_product_id;
    ELSE
        v_store := p_store;
    END IF;
    
    IF p_price IS NULL THEN
        SELECT COALESCE(harga, 0) INTO v_price FROM product WHERE productid = p_product_id;
    ELSE
        v_price := p_price;
    END IF;
    
    INSERT INTO stock_adjustment (productid, warehouseid, type, quantity, description, date, price, store)
    VALUES (p_product_id, p_warehouse_id, p_adj_type, p_quantity, p_description, v_transaction_date, v_price, v_store);
    
    IF p_adj_type = 'add' THEN
        INSERT INTO product_warehouse (productid, warehouseid, quantity)
        VALUES (p_product_id, p_warehouse_id, p_quantity)
        ON CONFLICT (productid, warehouseid) 
        DO UPDATE SET quantity = product_warehouse.quantity + p_quantity;
        
        UPDATE product 
        SET quantity = quantity + p_quantity, updateat = CURRENT_TIMESTAMP
        WHERE productid = p_product_id;
        
    ELSIF p_adj_type = 'reduce' THEN
        UPDATE product_warehouse 
        SET quantity = quantity - p_quantity
        WHERE productid = p_product_id AND warehouseid = p_warehouse_id;
        
        UPDATE product 
        SET quantity = quantity - p_quantity, updateat = CURRENT_TIMESTAMP
        WHERE productid = p_product_id;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- FUNGSI PEMBAYARAN UTANG SUPPLIER
CREATE OR REPLACE FUNCTION record_supplier_payment(
    p_debtid INTEGER,
    p_amount NUMERIC,
    p_note TEXT DEFAULT NULL,
    p_transaction_date TEXT DEFAULT NULL
)
RETURNS VOID AS $$
DECLARE
    v_transaction_date TIMESTAMP;
BEGIN
    IF p_transaction_date IS NOT NULL AND p_transaction_date != '' THEN
        v_transaction_date := p_transaction_date::TIMESTAMP;
    ELSE
        v_transaction_date := CURRENT_TIMESTAMP;
    END IF;
    
    UPDATE debt SET paid = paid + p_amount WHERE debtid = p_debtid;
    
    INSERT INTO payment_history (debtid, paidamount, paidat, description)
    VALUES (p_debtid, p_amount, v_transaction_date, p_note);
END;
$$ LANGUAGE plpgsql;

-- FUNGSI PEMBAYARAN PIUTANG PELANGGAN
CREATE OR REPLACE FUNCTION record_customer_payment(
    p_debtid INTEGER,
    p_amount NUMERIC,
    p_note TEXT DEFAULT NULL,
    p_transaction_date TEXT DEFAULT NULL
)
RETURNS VOID AS $$
DECLARE
    v_transaction_date TIMESTAMP;
BEGIN
    IF p_transaction_date IS NOT NULL AND p_transaction_date != '' THEN
        v_transaction_date := p_transaction_date::TIMESTAMP;
    ELSE
        v_transaction_date := CURRENT_TIMESTAMP;
    END IF;
    
    UPDATE debt SET paid = paid + p_amount WHERE debtid = p_debtid;
    
    INSERT INTO payment_history (debtid, paidamount, paidat, description)
    VALUES (p_debtid, p_amount, v_transaction_date, p_note);
END;
$$ LANGUAGE plpgsql;

-- FUNGSI BIAYA OPERASIONAL
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
BEGIN
    IF p_expense_date IS NOT NULL AND p_expense_date != '' THEN
        v_expense_date := p_expense_date::TIMESTAMP;
    ELSE
        v_expense_date := CURRENT_TIMESTAMP;
    END IF;
    
    INSERT INTO operational_expense (
        store, expense_type, amount, description, reference_id, 
        account_id, expense_date, created_by
    )
    VALUES (
        p_store, p_expense_type, p_amount, p_description, p_reference_id,
        p_account_id, v_expense_date, p_created_by
    )
    RETURNING expense_id INTO v_expense_id;
    
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
            v_balance_after, COALESCE(p_description, 'Biaya operasional: ' || p_expense_type), 
            v_expense_date, p_created_by
        );
    END IF;
    
    RETURN v_expense_id;
END;
$$ LANGUAGE plpgsql;

SELECT 'Function stok, pembayaran, expense selesai!' as status;
