-- =====================================================
-- FILE 5: CREATE FUNCTION - RETUR
-- (JALANKAN KELIMA)
-- =====================================================

-- FUNGSI RETUR PEMBELIAN
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
    p_created_by TEXT DEFAULT 'system'
)
RETURNS INTEGER AS $$
DECLARE
    v_return_id INTEGER;
    v_return_date TIMESTAMP;
    v_total_amount NUMERIC := 0;
    v_item JSONB;
    v_items JSONB;
    v_balance_after NUMERIC;
BEGIN
    IF p_return_date IS NOT NULL AND p_return_date != '' THEN
        v_return_date := p_return_date::TIMESTAMP;
    ELSE
        v_return_date := CURRENT_TIMESTAMP;
    END IF;
    
    v_items := p_items::JSONB;
    
    FOR v_item IN SELECT * FROM jsonb_array_elements(v_items)
    LOOP
        v_total_amount := v_total_amount + ((v_item->>'quantity')::INTEGER * (v_item->>'price')::NUMERIC);
    END LOOP;
    
    INSERT INTO purchase_return (
        store, supplier_id, warehouse_id, total_amount, return_type,
        status, reason, description, account_id, return_date, created_by
    )
    VALUES (
        p_store, p_supplier_id, p_warehouse_id, v_total_amount, p_return_type,
        'completed', p_reason, p_description, p_account_id, v_return_date, p_created_by
    )
    RETURNING return_id INTO v_return_id;
    
    FOR v_item IN SELECT * FROM jsonb_array_elements(v_items)
    LOOP
        INSERT INTO purchase_return_items (return_id, product_id, quantity, price)
        VALUES (v_return_id, (v_item->>'product_id')::INTEGER, (v_item->>'quantity')::INTEGER, (v_item->>'price')::NUMERIC);
        
        UPDATE product_warehouse 
        SET quantity = quantity - (v_item->>'quantity')::INTEGER
        WHERE productid = (v_item->>'product_id')::INTEGER AND warehouseid = p_warehouse_id;
        
        UPDATE product 
        SET quantity = quantity - (v_item->>'quantity')::INTEGER, updateat = CURRENT_TIMESTAMP
        WHERE productid = (v_item->>'product_id')::INTEGER;
    END LOOP;
    
    IF p_return_type = 'credit_note' THEN
        UPDATE debt SET paid = paid + v_total_amount
        WHERE debtid = (
            SELECT debtid FROM debt 
            WHERE type = 'supplier' AND store = p_store AND relatedid = p_supplier_id AND (amount - paid) > 0
            ORDER BY date ASC LIMIT 1
        );
    ELSIF p_return_type = 'refund' AND p_account_id IS NOT NULL THEN
        UPDATE accounts SET balance = balance + v_total_amount
        WHERE account_id = p_account_id
        RETURNING balance INTO v_balance_after;
        
        INSERT INTO account_transactions (
            account_id, transaction_type, related_id, amount, 
            balance_after, description, transaction_date, created_by
        )
        VALUES (
            p_account_id, 'purchase_return', v_return_id, v_total_amount,
            v_balance_after, COALESCE(p_description, 'Refund retur pembelian'), v_return_date, p_created_by
        );
    END IF;
    
    RETURN v_return_id;
END;
$$ LANGUAGE plpgsql;

-- FUNGSI RETUR PENJUALAN
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
    p_created_by TEXT DEFAULT 'system'
)
RETURNS INTEGER AS $$
DECLARE
    v_return_id INTEGER;
    v_return_date TIMESTAMP;
    v_total_amount NUMERIC := 0;
    v_item JSONB;
    v_items JSONB;
    v_balance_after NUMERIC;
BEGIN
    IF p_return_date IS NOT NULL AND p_return_date != '' THEN
        v_return_date := p_return_date::TIMESTAMP;
    ELSE
        v_return_date := CURRENT_TIMESTAMP;
    END IF;
    
    v_items := p_items::JSONB;
    
    FOR v_item IN SELECT * FROM jsonb_array_elements(v_items)
    LOOP
        v_total_amount := v_total_amount + ((v_item->>'quantity')::INTEGER * (v_item->>'price')::NUMERIC);
    END LOOP;
    
    INSERT INTO sale_return (
        store, customer_name, warehouse_id, total_amount, return_type,
        status, reason, description, account_id, return_date, created_by
    )
    VALUES (
        p_store, p_customer_name, p_warehouse_id, v_total_amount, p_return_type,
        'completed', p_reason, p_description, p_account_id, v_return_date, p_created_by
    )
    RETURNING return_id INTO v_return_id;
    
    FOR v_item IN SELECT * FROM jsonb_array_elements(v_items)
    LOOP
        INSERT INTO sale_return_items (return_id, product_id, quantity, price)
        VALUES (v_return_id, (v_item->>'product_id')::INTEGER, (v_item->>'quantity')::INTEGER, (v_item->>'price')::NUMERIC);
        
        INSERT INTO product_warehouse (productid, warehouseid, quantity)
        VALUES ((v_item->>'product_id')::INTEGER, p_warehouse_id, (v_item->>'quantity')::INTEGER)
        ON CONFLICT (productid, warehouseid) 
        DO UPDATE SET quantity = product_warehouse.quantity + (v_item->>'quantity')::INTEGER;
        
        UPDATE product 
        SET quantity = quantity + (v_item->>'quantity')::INTEGER, updateat = CURRENT_TIMESTAMP
        WHERE productid = (v_item->>'product_id')::INTEGER;
    END LOOP;
    
    IF p_return_type = 'refund' AND p_account_id IS NOT NULL THEN
        UPDATE accounts SET balance = balance - v_total_amount
        WHERE account_id = p_account_id
        RETURNING balance INTO v_balance_after;
        
        INSERT INTO account_transactions (
            account_id, transaction_type, related_id, amount, 
            balance_after, description, transaction_date, created_by
        )
        VALUES (
            p_account_id, 'sale_return', v_return_id, -v_total_amount,
            v_balance_after, COALESCE(p_description, 'Refund retur penjualan'), v_return_date, p_created_by
        );
    END IF;
    
    RETURN v_return_id;
END;
$$ LANGUAGE plpgsql;

SELECT 'Function retur selesai!' as status;
