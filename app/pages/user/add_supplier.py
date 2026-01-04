import streamlit as st
from app.db import get_client

def show():
    st.title("Tambahkan Supplier Baru")

    with st.form("add_supplier_form"):
        supplier_name = st.text_input("Nama Supplier*")
        supplier_no = st.text_input("Nomor Telepon")
        address = st.text_area("Alamat")
        description = st.text_area("Deskripsi")

        submitted = st.form_submit_button("Simpan Supplier")

        if submitted:
            if not supplier_name:
                st.warning("Nama Supplier wajib diisi.")
                return

            try:
                supabase = get_client()
                
                check_res = supabase.table("supplier").select("supplierid").eq("suppliername", supplier_name).execute()
                if check_res.data:
                    st.error(f"Supplier dengan nama '{supplier_name}' sudah ada.")
                    return

                data_to_insert = {
                    "suppliername": supplier_name,
                    "supplierno": supplier_no,
                    "address": address,
                    "description": description
                }
                
                response = supabase.table("supplier").insert(data_to_insert).execute()
                
                if response.data:
                    st.success(f"Supplier '{supplier_name}' berhasil ditambahkan.")
                    st.rerun()
                else:
                    st.error("Gagal menambahkan supplier. Silakan coba lagi.")

            except Exception as e:
                error_str = str(e)
                if "duplicate key" in error_str.lower() or "unique constraint" in error_str.lower():
                    st.error(f"Supplier '{supplier_name}' sudah terdaftar. Gunakan nama lain.")
                else:
                    st.error(f"Terjadi kesalahan: {error_str}")
