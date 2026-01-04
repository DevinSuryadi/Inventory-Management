import streamlit as st
from app.db import get_client
import pandas as pd
import io

def show():
    st.title("Impor Stok Awal dari Excel")
    st.warning("**Catatan:** Hal ini tidak memperbarui produk yang sudah ada.")

    store = st.session_state.get("store")
    if not store:
        st.warning("Sesi toko tidak valid. Silakan login kembali.")
        return

    supabase = get_client()

    # --- Bagian 1: Unduh Template ---
    st.markdown("---")
    st.subheader("1. Unduh Template Excel")

    # Buat template di memori
    template_df = pd.DataFrame({
        "Nama Produk": ["Contoh: Murano"],
        "Jumlah": [10],
        "Gudang": ["Gudang Bagongan"],
        "Harga Beli": [75000],
        "Supplier": ["Supplier Keramik"],
        "Jenis": ["Keramik"],
        "Ukuran": ["30x30"],
        "Warna": ["Putih"],
        "Merek": ["Tanpa Merek"],
        "Deskripsi": ["Deskripsi bebas..."]
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

    # --- Bagian 2: Unggah File ---
    st.markdown("---")
    st.subheader("2. Unggah File Excel yang Sudah Diisi")
    
    uploaded_file = st.file_uploader("Pilih file .xlsx", type=["xlsx"])

    if uploaded_file is not None:
        try:
            df = pd.read_excel(uploaded_file)
            
            # Validasi kolom
            required_columns = ["Nama Produk", "Jumlah", "Gudang", "Harga Beli", "Supplier"]
            missing_cols = [col for col in required_columns if col not in df.columns]
            
            if missing_cols:
                st.error(f"File Excel tidak valid. Kolom berikut tidak ditemukan: **{', '.join(missing_cols)}**")
            else:
                st.success("Preview Data:")
                st.dataframe(df.head(10)) # Tampilkan 10 baris pertama sebagai pratinjau

                # --- Bagian 3: Proses Impor ---
                st.markdown("---")
                st.subheader("3. Mulai Proses Impor")
                
                if st.button(f"Impor {len(df)} Produk", use_container_width=True):
                    # Ubah semua kolom menjadi string untuk dikirim sebagai JSON
                    df_json = df.astype(str).to_json(orient='records')
                    
                    with st.spinner("Proses.."):
                        # Panggil fungsi RPC di Supabase
                        result = supabase.rpc("bulk_import_products", {
                            "products_json": df_json,
                            "p_store": store
                        }).execute()
                    
                    if "Berhasil" in result.data:
                        st.success(result.data)
                        st.balloons()
                    else:
                        st.error(f"Terjadi kesalahan saat impor: {result.data}")

        except Exception as e:
            st.error(f"Gagal membaca file Excel. Pastikan formatnya benar. Detail error: {e}")
