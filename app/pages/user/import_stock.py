import streamlit as st
from app.db import get_client
import pandas as pd
import io

def show():
    st.title("Impor Stok Awal dari Excel")

    store = st.session_state.get("store")
    if not store:
        st.warning("Sesi toko tidak valid. Silakan login kembali.")
        return

    supabase = get_client()

    # Fetch existing warehouses and suppliers for reference
    warehouses = supabase.table("warehouse_list").select("warehouseid, name").execute()
    suppliers = supabase.table("supplier").select("supplierid, suppliername").execute()
    
    warehouse_list = warehouses.data if warehouses.data else []
    supplier_list = suppliers.data if suppliers.data else []
    
    warehouse_names = [w['name'] for w in warehouse_list]
    supplier_names = [s['suppliername'] for s in supplier_list]

    # Check if warehouses exist
    if not warehouse_list:
        st.error("⚠️ Belum ada gudang yang terdaftar.")
        return

    # Info Section
    st.markdown("---")
    st.subheader("Informasi Referensi")
    
    col_info1, col_info2 = st.columns(2)
    with col_info1:
        st.markdown("**Gudang yang Tersedia:**")
        for w in warehouse_names:
            st.markdown(f"- `{w}`")
    
    with col_info2:
        st.markdown("**Supplier yang Tersedia:**")
        if supplier_names:
            for s in supplier_names:
                st.markdown(f"- `{s}`")
        else:
            st.markdown("_Belum ada supplier(Otomatis)")

    # Download Template
    st.markdown("---")
    st.subheader("1. Unduh Template Excel")

    example_warehouse = warehouse_names[0] if warehouse_names else "Nama Gudang"
    example_supplier = supplier_names[0] if supplier_names else "Nama Supplier"
    
    template_df = pd.DataFrame({
        "Nama Produk": ["Contoh: Granit Murano 60x60", "Keramik Putih 30x30"],
        "Jumlah": [100, 50],
        "Gudang": [example_warehouse, example_warehouse],
        "Harga Beli": [75000, 25000],
        "Supplier": [example_supplier, example_supplier],
        "Jenis": ["Granit", "Keramik"],
        "Ukuran": ["60x60", "30x30"],
        "Warna": ["Abu-abu", "Putih"],
        "Merek": ["Murano", "Roman"],
        "Deskripsi": ["...", "..."]
    })
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        template_df.to_excel(writer, index=False, sheet_name='Data Produk')
    
    st.download_button(
        label="Unduh Template (.xlsx)",
        data=output.getvalue(),
        file_name="template_import_produk.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    
    st.caption("""
    **Keterangan kolom:**
    - **Nama Produk** (wajib): Nama produk yang akan didaftarkan
    - **Jumlah** (wajib): Stok awal produk
    - **Gudang** (wajib): Nama gudang tempat penyimpanan (harus sesuai dengan daftar di atas)
    - **Harga Beli** (wajib): Harga modal/beli per satuan
    - **Supplier** (wajib): Nama supplier (jika belum ada dibuat otomatis)
    - **Jenis, Ukuran, Warna, Merek, Deskripsi**: Opsional
    """)

    # Upload File
    st.markdown("---")
    st.subheader("2. Unggah File Excel yang Sudah Diisi")
    
    uploaded_file = st.file_uploader("Pilih file .xlsx", type=["xlsx"])

    if uploaded_file is not None:
        try:
            df = pd.read_excel(uploaded_file)
            
            required_columns = ["Nama Produk", "Jumlah", "Gudang", "Harga Beli", "Supplier"]
            missing_cols = [col for col in required_columns if col not in df.columns]
            
            if missing_cols:
                st.error(f"❌ File Excel tidak valid. Kolom berikut tidak ditemukan: **{', '.join(missing_cols)}**")
            else:
                df = df.dropna(subset=["Nama Produk"])
                df = df[df["Nama Produk"].astype(str).str.strip() != ""]
                
                if len(df) == 0:
                    st.warning("File tidak berisi data produk yang valid.")
                    return
                
                st.success(f"✅ File valid! Ditemukan **{len(df)} produk** untuk diimpor.")
                
                # Validate warehouses in uploaded file
                df_warehouses = df["Gudang"].dropna().unique().tolist()
                invalid_warehouses = [w for w in df_warehouses if w.strip().lower() not in [wh.lower() for wh in warehouse_names]]
                
                if invalid_warehouses:
                    st.error(f"❌ Gudang tidak valid ditemukan di file: **{', '.join(invalid_warehouses)}**")
                    return
                
                # Show preview
                st.markdown("**Preview Data:**")
                st.dataframe(df, use_container_width=True)
                
                # Summary
                col_sum1, col_sum2, col_sum3 = st.columns(3)
                with col_sum1:
                    st.metric("Total Produk", len(df))
                with col_sum2:
                    total_qty = df["Jumlah"].sum() if "Jumlah" in df.columns else 0
                    st.metric("Total Stok", f"{int(total_qty):,}")
                with col_sum3:
                    total_value = (df["Jumlah"] * df["Harga Beli"]).sum() if "Jumlah" in df.columns and "Harga Beli" in df.columns else 0
                    st.metric("Total Nilai", f"Rp {total_value:,.0f}")

                # Import Process
                st.markdown("---")
                st.subheader("3. Mulai Proses Impor")
                
                st.warning(f"Impor **{len(df)} produk** ke database.")
                
                confirm = st.checkbox("✅ Data sudah benar dan siap diimpor")
                
                if st.button(f"Impor {len(df)} Produk", use_container_width=True, type="primary"):
                    if not confirm:
                        st.error("Harap centang konfirmasi terlebih dahulu!")
                    else:
                        df_clean = df.fillna("")
                        df_json = df_clean.astype(str).to_json(orient='records')
                        
                        with st.spinner("Sedang mengimpor data ke database..."):
                            try:
                                result = supabase.rpc("bulk_import_products", {
                                    "products_json": df_json,
                                    "p_store": store
                                }).execute()
                                
                                if result.data and "Berhasil" in str(result.data):
                                    st.success(f"✅ {result.data}")
                                    st.balloons()
                                    st.info("Silakan cek halaman **Lihat Stok** untuk melihat produk yang telah diimpor.")
                                else:
                                    st.error(f"Terjadi kesalahan saat impor: {result.data}")
                            except Exception as e:
                                st.error(f"Gagal menjalankan impor: {str(e)}")

        except Exception as e:
            st.error(f"Gagal membaca file Excel. Detail error: {e}")
