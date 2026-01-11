import streamlit as st
from app.db import get_client

def show():
    st.title("➕ Tambahkan Supplier Baru")


    if "add_supplier_form_key" not in st.session_state:
        st.session_state.add_supplier_form_key = 0

    with st.form(f"add_supplier_form_{st.session_state.add_supplier_form_key}"):
        supplier_name = st.text_input("Nama Supplier*")
        supplier_no = st.text_input("Nomor Telepon")
        address = st.text_area("Alamat")
        description = st.text_area("Deskripsi")

        st.divider()
        confirm = st.checkbox("Data supplier sudah benar")
        submitted = st.form_submit_button("Daftarkan Supplier", use_container_width=True, type="primary")

        if submitted:
            if not confirm:
                st.error("Harap centang konfirmasi terlebih dahulu!")
                st.stop()
            if not supplier_name.strip():
                st.warning("Nama Supplier wajib diisi.")
                return

            try:
                supabase = get_client()
                
                check_res = supabase.table("supplier").select("supplierid").eq("suppliername", supplier_name.strip()).execute()
                if check_res.data:
                    st.error(f"Supplier dengan nama '{supplier_name}' sudah ada.")
                    return

                data_to_insert = {
                    "suppliername": supplier_name.strip(),
                    "supplierno": supplier_no.strip() if supplier_no.strip() else None,
                    "address": address.strip() if address.strip() else None,
                    "description": description.strip() if description.strip() else None
                }
                
                response = supabase.table("supplier").insert(data_to_insert).execute()
                
                if response.data:
                    st.success(f"✅ Supplier '{supplier_name}' berhasil ditambahkan.")
                    st.session_state.add_supplier_form_key += 1
                    st.rerun()
                else:
                    st.error("Gagal menambahkan supplier. Silakan coba lagi.")

            except Exception as e:
                error_str = str(e)
                if "duplicate key" in error_str.lower() or "unique constraint" in error_str.lower():
                    st.error(f"Supplier '{supplier_name}' sudah terdaftar. Gunakan nama lain.")
                else:
                    st.error(f"Terjadi kesalahan: {error_str}")
