import streamlit as st
from app.db import get_client

def show():
    st.title("Register Stock")

    # Ambil informasi toko dari session
    store = st.session_state.get("store")
    if not store:
        st.warning("Sesi tidak valid. Silakan login kembali.")
        return

    with st.form("register_stock_form"):
        product_name = st.text_input("Nama Produk*")
        type_ = st.text_input("Jenis")
        size = st.text_input("Ukuran")
        color = st.text_input("Warna")
        brand = st.text_input("Merek") 
        description = st.text_area("Deskripsi (Opsional)")

        submitted = st.form_submit_button("Daftarkan Produk")

        if submitted:
            # Validasi input wajib
            if not product_name:
                st.warning("Nama Produk wajib diisi.")
                return

            try:
                supabase = get_client()

                data_to_insert = {
                    "store": store,
                    "productname": product_name,
                    "type": type_,
                    "size": size,
                    "color": color,
                    "brand": brand,
                    "description": description
                }
                
                response = supabase.table("product").insert(data_to_insert).execute()
                
                if response.data:
                    st.success(f"Produk '{product_name}' berhasil didaftarkan!")
                    st.rerun()
                else:
                    st.error("Gagal mendaftarkan produk. Silakan coba lagi.")
            
            except Exception as e:
                error_str = str(e)
                if "duplicate key" in error_str.lower() or "unique constraint" in error_str.lower():
                    st.error(f"Produk '{product_name}' sudah terdaftar di toko ini. Gunakan nama lain.")
                elif "foreign key" in error_str.lower():
                    st.error("Toko yang dipilih tidak valid. Silakan coba lagi.")
                else:
                    st.error(f"Terjadi kesalahan saat mendaftarkan produk: {error_str}")
