# =====================================================
# PANDUAN MIGRASI DATABASE - STORE ISOLATION
# =====================================================

## URUTAN MENJALANKAN FILE SQL

Jalankan file-file berikut di Supabase SQL Editor SECARA BERURUTAN:

### 1. step1_migrate_tables.sql
- Menambahkan kolom `store` ke tabel `warehouse_list` dan `supplier`
- Menghapus constraint lama
- Membuat index baru

### 2. step2_drop_functions.sql
- Menghapus SEMUA versi fungsi yang duplikat
- Menggunakan dynamic SQL untuk memastikan semua versi terhapus

### 3. step3_create_func_basic.sql
- record_stock_adjustment
- record_supplier_payment
- record_customer_payment
- record_operational_expense

### 4. step4_create_func_transaction.sql
- record_purchase_transaction_multi
- record_sale_transaction_multi

### 5. step5_create_func_return.sql
- record_purchase_return
- record_sale_return

### 6. step6_create_func_helper.sql
- get_supplier_debt_total
- get_supplier_debts
- get_customer_debts
- adjust_account_balance
- transfer_funds
- get_daily_sales_summary
- get_daily_purchase_summary
- get_stock_value_by_warehouse

### 7. step7_create_func_import.sql
- bulk_import_smart (FUNGSI UTAMA IMPORT)
- get_suppliers_view
- get_low_stock_products
- get_product_movement_history

## TROUBLESHOOTING

### Error: "column store does not exist"
Pastikan step1_migrate_tables.sql sudah dijalankan terlebih dahulu.

### Error: PGRST203 (function is not unique)
Jalankan step2_drop_functions.sql untuk menghapus semua versi duplikat.

### Error saat menjalankan fungsi
Periksa apakah semua step sebelumnya sudah berhasil dijalankan.

## VERIFIKASI

Setelah semua step dijalankan, verifikasi dengan query:

```sql
-- Cek kolom store di warehouse_list
SELECT column_name FROM information_schema.columns 
WHERE table_name = 'warehouse_list' AND column_name = 'store';

-- Cek kolom store di supplier
SELECT column_name FROM information_schema.columns 
WHERE table_name = 'supplier' AND column_name = 'store';

-- Cek fungsi bulk_import_smart
SELECT proname, pg_get_function_arguments(oid) 
FROM pg_proc WHERE proname = 'bulk_import_smart';
```

Pastikan:
1. Kolom `store` ada di kedua tabel
2. Hanya ada SATU versi fungsi `bulk_import_smart`
