import streamlit as st
import pandas as pd
from app.db import get_client

def show():
    st.title("Daftar Gudang (Global)")
    st.info("Gudang bersifat global dan dapat digunakan oleh semua toko.")

    try:
        supabase = get_client()

        response = supabase.table("warehouse_list").select("warehouseid, name").order("name", desc=False).execute()

        warehouses = response.data
        if warehouses:
            df = pd.DataFrame(warehouses).rename(columns={
                "warehouseid": "ID Gudang",
                "name": "Nama Gudang"
            })

            search_term = st.text_input("Cari berdasarkan Nama Gudang")

            if search_term:
                df = df[df['Nama Gudang'].str.contains(search_term, case=False, na=False)]
            
            if df.empty:
                st.warning(f"Tidak ada gudang yang cocok dengan pencarian '{search_term}'.")
            else:
                st.data_editor(
                    df,
                    use_container_width=True,
                    hide_index=True,
                    disabled=True
                )
        else:
            st.info("Belum ada gudang yang terdaftar.")

    except Exception as e:
        st.error(f"Terjadi kesalahan: {e}")
