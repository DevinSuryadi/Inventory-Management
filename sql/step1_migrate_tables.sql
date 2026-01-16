-- =====================================================
-- FILE 1: MIGRASI TABEL (JALANKAN PERTAMA)
-- =====================================================
-- File ini menambahkan kolom store ke tabel yang sudah ada

-- Tambah kolom store ke warehouse_list
ALTER TABLE warehouse_list ADD COLUMN IF NOT EXISTS store VARCHAR;

-- Tambah kolom store ke supplier
ALTER TABLE supplier ADD COLUMN IF NOT EXISTS store VARCHAR;

-- Hapus constraint lama jika ada
ALTER TABLE warehouse_list DROP CONSTRAINT IF EXISTS warehouse_list_name_key;
ALTER TABLE supplier DROP CONSTRAINT IF EXISTS supplier_suppliername_key;

-- Hapus constraint expense_type jika ada
ALTER TABLE operational_expense DROP CONSTRAINT IF EXISTS operational_expense_expense_type_check;

-- Index untuk performa
CREATE INDEX IF NOT EXISTS idx_warehouse_store ON warehouse_list(store);
CREATE INDEX IF NOT EXISTS idx_supplier_store ON supplier(store);

SELECT 'Migrasi tabel selesai!' as status;
