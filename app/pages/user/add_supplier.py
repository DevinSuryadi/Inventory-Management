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
                
                # Cek duplikasi nama supplier
                check_res = supabase.table("supplier").select("supplierid").eq("suppliername", supplier_name).execute()
                if check_res.data:
                    st.error(f"Supplier dengan nama '{supplier_name}' sudah ada.")
                    return

                # Insert data baru
                data_to_insert = {
                    "suppliername": supplier_name,
                    "supplierno": supplier_no,
                    "address": address,
                    "description": description
                }
                
                supabase.table("supplier").insert(data_to_insert).execute()


                st.success(f"Supplier '{supplier_name}' berhasil ditambahkan.")

            except Exception as e:
                st.error(f"Terjadi kesalahan: {e}")
