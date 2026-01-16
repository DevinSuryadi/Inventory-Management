-- =====================================================
-- FILE 2: DROP SEMUA FUNGSI DUPLIKAT (JALANKAN KEDUA)
-- =====================================================

DO $$ 
DECLARE 
    r RECORD;
    func_names TEXT[] := ARRAY[
        'bulk_import_smart',
        'get_suppliers_view',
        'record_stock_adjustment',
        'record_supplier_payment',
        'record_customer_payment',
        'record_operational_expense',
        'record_purchase_transaction_multi',
        'record_sale_transaction_multi',
        'record_purchase_return',
        'record_sale_return',
        'get_supplier_debt_total',
        'create_default_cash_account',
        'adjust_account_balance',
        'transfer_funds',
        'get_supplier_debts',
        'get_supplier_debts_with_top',
        'get_customer_debts',
        'get_customer_debts_with_top'
    ];
    func_name TEXT;
BEGIN
    FOREACH func_name IN ARRAY func_names
    LOOP
        FOR r IN 
            SELECT p.oid::regprocedure::text as func_signature
            FROM pg_proc p
            JOIN pg_namespace n ON p.pronamespace = n.oid
            WHERE n.nspname = 'public' 
            AND p.proname = func_name
        LOOP
            EXECUTE 'DROP FUNCTION IF EXISTS ' || r.func_signature || ' CASCADE';
            RAISE NOTICE 'Dropped: %', r.func_signature;
        END LOOP;
    END LOOP;
END $$;

SELECT 'Drop semua fungsi duplikat selesai!' as status;
