-- =====================================================
-- FIX DATA LAMA: Tambahkan ke productsupply
-- Jalankan setelah fix_all_v3.sql berhasil
-- =====================================================

-- Cek data yang perlu difix (produk yang tidak ada di productsupply)
SELECT p.productid, p.productname, p.harga, p.quantity
FROM product p
WHERE NOT EXISTS (
    SELECT 1 FROM productsupply ps WHERE ps.productid = p.productid
)
AND p.quantity > 0;

-- Jika ingin menambahkan productsupply untuk produk yang sudah ada,
-- Anda perlu tahu supplier_id yang akan digunakan.
-- Contoh: Jika supplier_id default adalah 1

-- INSERT INTO productsupply (productid, supplierid, quantity, price, date)
-- SELECT p.productid, 1, p.quantity, COALESCE(p.harga, 0), COALESCE(p.updateat, NOW())
-- FROM product p
-- WHERE NOT EXISTS (
--     SELECT 1 FROM productsupply ps WHERE ps.productid = p.productid
-- )
-- AND p.quantity > 0;

-- Untuk melihat supplier yang tersedia per store:
SELECT supplierid, suppliername, store FROM supplier ORDER BY store, suppliername;
