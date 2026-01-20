import streamlit as st
from app.db import get_client

def show():
    st.title("Tambahkan Gudang Baru")

    if "register_warehouse_form_key" not in st.session_state:
        st.session_state.register_warehouse_form_key = 0

    with st.form(f"register_warehouse_form_{st.session_state.register_warehouse_form_key}"):
        warehouse_name = st.text_input("Nama Gudang*")
        
        st.divider()
        confirm = st.checkbox("Data gudang ini benar")
        submitted = st.form_submit_button("Simpan Gudang", use_container_width=True, type="primary")
        if submitted:
            if not confirm:
                st.error("Harap centang konfirmasi terlebih dahulu!")
                st.stop()
            if not warehouse_name.strip():
                st.warning("Nama gudang tidak boleh kosong.")
                return

            try:
                supabase = get_client()
                store = st.session_state.get("store")
                
                if not store:
                    st.error("Sesi toko tidak valid. Silakan login kembali.")
                    return
                
                check_res = supabase.table("warehouse_list").select("warehouseid").eq("store", store).eq("name", warehouse_name.strip()).execute()
                if check_res.data:
                    st.error(f"Gudang dengan nama '{warehouse_name}' sudah ada di toko ini.")
                    return

                response = supabase.table("warehouse_list").insert({"store": store, "name": warehouse_name.strip()}).execute()
                
                if response.data:
                    st.success(f"✅ Gudang '{warehouse_name}' berhasil ditambahkan.")
                    st.session_state.register_warehouse_form_key += 1
                    st.rerun()
                else:
                    st.error("Gagal menambahkan gudang. Silakan coba lagi.")
            
            except Exception as e:
                error_str = str(e)
                if "duplicate key" in error_str.lower() or "unique constraint" in error_str.lower():
                    st.error(f"Nama gudang '{warehouse_name}' sudah terdaftar")
                else:
                    st.error(f"Terjadi kesalahan: {error_str}")
