-- =====================================================
-- FILE 6: CREATE FUNCTION - HELPER
-- (JALANKAN KEENAM)
-- =====================================================

-- GET SUPPLIER DEBT TOTAL
CREATE OR REPLACE FUNCTION get_supplier_debt_total(p_store TEXT)
RETURNS NUMERIC AS $$
DECLARE
    v_total NUMERIC;
BEGIN
    SELECT COALESCE(SUM(amount - paid), 0) INTO v_total
    FROM debt
    WHERE type = 'supplier' AND store = p_store;
    
    RETURN v_total;
END;
$$ LANGUAGE plpgsql;

-- GET SUPPLIER DEBTS
CREATE OR REPLACE FUNCTION get_supplier_debts(p_store TEXT)
RETURNS TABLE (
    supplier_id INTEGER,
    supplier_name TEXT,
    total_debt NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        d.relatedid::INTEGER as supplier_id,
        s.suppliername::TEXT as supplier_name,
        COALESCE(SUM(d.amount - d.paid), 0) as total_debt
    FROM debt d
    JOIN supplier s ON d.relatedid = s.supplierid
    WHERE d.type = 'supplier' AND d.store = p_store
    GROUP BY d.relatedid, s.suppliername
    HAVING COALESCE(SUM(d.amount - d.paid), 0) > 0;
END;
$$ LANGUAGE plpgsql;

-- GET CUSTOMER DEBTS
CREATE OR REPLACE FUNCTION get_customer_debts(p_store TEXT)
RETURNS TABLE (
    customer_name TEXT,
    total_debt NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        d.relatedname::TEXT as customer_name,
        COALESCE(SUM(d.amount - d.paid), 0) as total_debt
    FROM debt d
    WHERE d.type = 'customer' AND d.store = p_store
    GROUP BY d.relatedname
    HAVING COALESCE(SUM(d.amount - d.paid), 0) > 0;
END;
$$ LANGUAGE plpgsql;

-- ADJUST ACCOUNT BALANCE
CREATE OR REPLACE FUNCTION adjust_account_balance(
    p_account_id INTEGER,
    p_amount NUMERIC,
    p_adjustment_type TEXT,
    p_description TEXT DEFAULT NULL,
    p_created_by TEXT DEFAULT 'system'
)
RETURNS NUMERIC AS $$
DECLARE
    v_balance_after NUMERIC;
    v_actual_amount NUMERIC;
BEGIN
    IF p_adjustment_type = 'add' THEN
        v_actual_amount := p_amount;
    ELSIF p_adjustment_type = 'subtract' THEN
        v_actual_amount := -p_amount;
    ELSE
        v_actual_amount := p_amount;
    END IF;
    
    UPDATE accounts SET balance = balance + v_actual_amount
    WHERE account_id = p_account_id
    RETURNING balance INTO v_balance_after;
    
    INSERT INTO account_transactions (
        account_id, transaction_type, amount, 
        balance_after, description, transaction_date, created_by
    )
    VALUES (
        p_account_id, 'adjustment', v_actual_amount,
        v_balance_after, COALESCE(p_description, 'Penyesuaian saldo'), CURRENT_TIMESTAMP, p_created_by
    );
    
    RETURN v_balance_after;
END;
$$ LANGUAGE plpgsql;

-- TRANSFER FUNDS BETWEEN ACCOUNTS
CREATE OR REPLACE FUNCTION transfer_funds(
    p_from_account INTEGER,
    p_to_account INTEGER,
    p_amount NUMERIC,
    p_description TEXT DEFAULT NULL,
    p_created_by TEXT DEFAULT 'system'
)
RETURNS BOOLEAN AS $$
DECLARE
    v_from_balance NUMERIC;
    v_to_balance NUMERIC;
BEGIN
    -- Reduce from source account
    UPDATE accounts SET balance = balance - p_amount
    WHERE account_id = p_from_account
    RETURNING balance INTO v_from_balance;
    
    INSERT INTO account_transactions (
        account_id, transaction_type, amount, 
        balance_after, description, transaction_date, created_by
    )
    VALUES (
        p_from_account, 'transfer_out', -p_amount,
        v_from_balance, COALESCE(p_description, 'Transfer keluar'), CURRENT_TIMESTAMP, p_created_by
    );
    
    -- Add to destination account
    UPDATE accounts SET balance = balance + p_amount
    WHERE account_id = p_to_account
    RETURNING balance INTO v_to_balance;
    
    INSERT INTO account_transactions (
        account_id, transaction_type, amount, 
        balance_after, description, transaction_date, created_by
    )
    VALUES (
        p_to_account, 'transfer_in', p_amount,
        v_to_balance, COALESCE(p_description, 'Transfer masuk'), CURRENT_TIMESTAMP, p_created_by
    );
    
    RETURN TRUE;
END;
$$ LANGUAGE plpgsql;

-- GET DAILY SALES SUMMARY
CREATE OR REPLACE FUNCTION get_daily_sales_summary(
    p_store TEXT,
    p_start_date DATE,
    p_end_date DATE
)
RETURNS TABLE (
    sale_date DATE,
    total_transactions BIGINT,
    total_sales NUMERIC,
    total_cash NUMERIC,
    total_credit NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        DATE(s.transactiondate) as sale_date,
        COUNT(*)::BIGINT as total_transactions,
        COALESCE(SUM(s.totalamount), 0) as total_sales,
        COALESCE(SUM(CASE WHEN s.paymenttype = 'cash' THEN s.totalamount ELSE 0 END), 0) as total_cash,
        COALESCE(SUM(CASE WHEN s.paymenttype = 'credit' THEN s.totalamount ELSE 0 END), 0) as total_credit
    FROM transaction t
    JOIN sale s ON t.transactionid = s.transactionid
    WHERE t.store = p_store 
        AND t.type = 'sale'
        AND DATE(s.transactiondate) BETWEEN p_start_date AND p_end_date
    GROUP BY DATE(s.transactiondate)
    ORDER BY DATE(s.transactiondate);
END;
$$ LANGUAGE plpgsql;

-- GET DAILY PURCHASE SUMMARY
CREATE OR REPLACE FUNCTION get_daily_purchase_summary(
    p_store TEXT,
    p_start_date DATE,
    p_end_date DATE
)
RETURNS TABLE (
    purchase_date DATE,
    total_transactions BIGINT,
    total_purchases NUMERIC,
    total_cash NUMERIC,
    total_credit NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        DATE(p.transactiondate) as purchase_date,
        COUNT(*)::BIGINT as total_transactions,
        COALESCE(SUM(p.totalamount), 0) as total_purchases,
        COALESCE(SUM(CASE WHEN p.paymenttype = 'cash' THEN p.totalamount ELSE 0 END), 0) as total_cash,
        COALESCE(SUM(CASE WHEN p.paymenttype = 'credit' THEN p.totalamount ELSE 0 END), 0) as total_credit
    FROM transaction t
    JOIN purchase p ON t.transactionid = p.transactionid
    WHERE t.store = p_store 
        AND t.type = 'purchase'
        AND DATE(p.transactiondate) BETWEEN p_start_date AND p_end_date
    GROUP BY DATE(p.transactiondate)
    ORDER BY DATE(p.transactiondate);
END;
$$ LANGUAGE plpgsql;

-- GET STOCK VALUE BY WAREHOUSE
CREATE OR REPLACE FUNCTION get_stock_value_by_warehouse(p_store TEXT)
RETURNS TABLE (
    warehouse_id INTEGER,
    warehouse_name TEXT,
    total_items BIGINT,
    total_quantity NUMERIC,
    total_value NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        w.warehouseid::INTEGER as warehouse_id,
        w.warehousename::TEXT as warehouse_name,
        COUNT(DISTINCT pw.productid)::BIGINT as total_items,
        COALESCE(SUM(pw.quantity), 0)::NUMERIC as total_quantity,
        COALESCE(SUM(pw.quantity * p.purchaseprice), 0)::NUMERIC as total_value
    FROM warehouse_list w
    LEFT JOIN product_warehouse pw ON w.warehouseid = pw.warehouseid
    LEFT JOIN product p ON pw.productid = p.productid
    WHERE w.store = p_store
    GROUP BY w.warehouseid, w.warehousename
    ORDER BY w.warehousename;
END;
$$ LANGUAGE plpgsql;

SELECT 'Function helper selesai!' as status;
