import streamlit as st
from app.db import get_client

def show():
    st.title("Tambahkan Gudang Baru")

    with st.form("register_warehouse_form"):
        warehouse_name = st.text_input("Nama Gudang*")
        submitted = st.form_submit_button("Simpan Gudang")

        if submitted:
            if not warehouse_name.strip():
                st.warning("Nama gudang tidak boleh kosong.")
                return

            try:
                supabase = get_client()
                
                check_res = supabase.table("warehouse_list").select("warehouseid", count='exact').eq("name", warehouse_name).execute()
                if check_res.count > 0:
                    st.error(f"Gudang dengan nama '{warehouse_name}' sudah ada.")
                    return

                # Insert data ke tabel 'warehouse_list'
                supabase.table("warehouse_list").insert({"name": warehouse_name}).execute()

                st.success(f"Gudang '{warehouse_name}' berhasil ditambahkan.")
                st.rerun()
            
            except Exception as e:
                st.error(f"Terjadi kesalahan: {e}")
