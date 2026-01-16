-- =====================================================
-- FILE 4: CREATE FUNCTION - PEMBELIAN & PENJUALAN
-- (JALANKAN KEEMPAT)
-- =====================================================

-- FUNGSI PEMBELIAN MULTI-ITEM
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
    p_created_by TEXT DEFAULT 'system'
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
    
    INSERT INTO purchase_transaction (
        store, supplier_id, warehouse_id, total_amount, payment_type, 
        due_date, account_id, description, transaction_date, created_by
    )
    VALUES (
        p_store, p_supplier_id, p_warehouse_id, v_total_amount, p_payment_type,
        v_due_date, p_account_id, p_description, v_transaction_date, p_created_by
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
    END LOOP;
    
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
            v_balance_after, COALESCE(p_description, 'Pembelian'), v_transaction_date, p_created_by
        );
    ELSIF p_payment_type = 'credit' THEN
        INSERT INTO debt (type, relatedid, amount, paid, date, description, store, due_date)
        VALUES ('supplier', p_supplier_id, v_total_amount, 0, v_transaction_date, p_description, p_store, v_due_date);
    END IF;
    
    RETURN v_transaction_id;
END;
$$ LANGUAGE plpgsql;

-- FUNGSI PENJUALAN MULTI-ITEM
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
    p_created_by TEXT DEFAULT 'system'
)
RETURNS INTEGER AS $$
DECLARE
    v_transaction_id INTEGER;
    v_transaction_date TIMESTAMP;
    v_due_date TIMESTAMP;
    v_total_amount NUMERIC := 0;
    v_item JSONB;
    v_items JSONB;
    v_current_stock INTEGER;
    v_balance_after NUMERIC;
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
        
        SELECT COALESCE(quantity, 0) INTO v_current_stock
        FROM product_warehouse
        WHERE productid = (v_item->>'product_id')::INTEGER AND warehouseid = p_warehouse_id;
        
        IF v_current_stock < (v_item->>'quantity')::INTEGER THEN
            RAISE EXCEPTION 'Stok tidak mencukupi untuk product_id %', (v_item->>'product_id')::INTEGER;
        END IF;
    END LOOP;
    
    INSERT INTO sale_transaction (
        store, warehouse_id, customer_name, total_amount, payment_type, 
        due_date, account_id, description, transaction_date, created_by
    )
    VALUES (
        p_store, p_warehouse_id, p_customer_name, v_total_amount, p_payment_type,
        v_due_date, p_account_id, p_description, v_transaction_date, p_created_by
    )
    RETURNING transaction_id INTO v_transaction_id;
    
    FOR v_item IN SELECT * FROM jsonb_array_elements(v_items)
    LOOP
        INSERT INTO sale_transaction_items (transaction_id, product_id, quantity, price)
        VALUES (v_transaction_id, (v_item->>'product_id')::INTEGER, (v_item->>'quantity')::INTEGER, (v_item->>'price')::NUMERIC);
        
        UPDATE product_warehouse 
        SET quantity = quantity - (v_item->>'quantity')::INTEGER
        WHERE productid = (v_item->>'product_id')::INTEGER AND warehouseid = p_warehouse_id;
        
        UPDATE product 
        SET quantity = quantity - (v_item->>'quantity')::INTEGER, updateat = CURRENT_TIMESTAMP
        WHERE productid = (v_item->>'product_id')::INTEGER;
    END LOOP;
    
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
            v_balance_after, COALESCE(p_description, 'Penjualan'), v_transaction_date, p_created_by
        );
    ELSIF p_payment_type = 'credit' THEN
        INSERT INTO debt (type, relatedid, amount, paid, date, description, store, due_date)
        VALUES ('customer', v_transaction_id, v_total_amount, 0, v_transaction_date, p_description, p_store, v_due_date);
    END IF;
    
    RETURN v_transaction_id;
END;
$$ LANGUAGE plpgsql;

SELECT 'Function pembelian & penjualan selesai!' as status;
