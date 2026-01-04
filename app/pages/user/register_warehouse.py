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
                response = supabase.table("warehouse_list").insert({"name": warehouse_name}).execute()
                
                if response.data:
                    st.success(f"Gudang '{warehouse_name}' berhasil ditambahkan.")
                    st.rerun()
                else:
                    st.error("Gagal menambahkan gudang. Silakan coba lagi.")
            
            except Exception as e:
                error_str = str(e)
                if "duplicate key" in error_str.lower() or "unique constraint" in error_str.lower():
                    st.error(f"Nama gudang '{warehouse_name}' sudah terdaftar. Gunakan nama lain.")
                else:
                    st.error(f"Terjadi kesalahan: {error_str}")
