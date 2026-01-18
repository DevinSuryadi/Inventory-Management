import streamlit as st
from app.db import get_client

def show():
    st.title("Register Stock")

    store = st.session_state.get("store")
    if not store:
        st.warning("Sesi tidak valid. Silakan login kembali.")
        return

    if "register_stock_form_key" not in st.session_state:
        st.session_state.register_stock_form_key = 0

    with st.form(f"register_stock_form_{st.session_state.register_stock_form_key}"):
        product_name = st.text_input("Nama Produk*")
        type_ = st.text_input("Jenis")
        size = st.text_input("Ukuran")
        color = st.text_input("Warna")
        brand = st.text_input("Merek") 
        description = st.text_area("Deskripsi (Opsional)")

        st.divider()
        confirm = st.checkbox("Data produk ini benar")
        submitted = st.form_submit_button("Daftarkan Produk", use_container_width=True, type="primary")

        if submitted:
            if not confirm:
                st.error("Harap centang konfirmasi terlebih dahulu!")
                st.stop()
            if not product_name.strip():
                st.warning("Nama Produk wajib diisi.")
                return

            try:
                supabase = get_client()

                data_to_insert = {
                    "store": store,
                    "productname": product_name.strip(),
                    "type": type_.strip() if type_.strip() else None,
                    "size": size.strip() if size.strip() else None,
                    "color": color.strip() if color.strip() else None,
                    "brand": brand.strip() if brand.strip() else None,
                    "description": description.strip() if description.strip() else None
                }
                
                response = supabase.table("product").insert(data_to_insert).execute()
                
                if response.data:
                    st.success(f"✅ Produk '{product_name}' berhasil didaftarkan!")
                    st.session_state.register_stock_form_key += 1
                    st.rerun()
                else:
                    st.error("Gagal mendaftarkan produk. Silakan coba lagi.")
            
            except Exception as e:
                error_str = str(e)
                if "duplicate key" in error_str.lower() or "unique constraint" in error_str.lower():
                    st.error(f"Produk '{product_name}' sudah terdaftar di toko ini")
                elif "foreign key" in error_str.lower():
                    st.error("Toko yang dipilih tidak valid. Silakan coba lagi.")
                else:
                    st.error(f"Terjadi kesalahan saat mendaftarkan produk: {error_str}")
