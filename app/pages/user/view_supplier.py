import streamlit as st
import pandas as pd
from app.db import get_client

def show():
    st.title("Daftar Supplier")

    store = st.session_state.get("store")
    if not store:
        st.warning("Sesi toko tidak valid. Silakan login kembali.")
        return

    try:
        supabase = get_client()
        response = supabase.rpc("get_suppliers_view", {"store_input": store}).execute()

        suppliers = response.data
        if not suppliers:
            st.info("Belum ada supplier yang terdaftar.")
            return

        df = pd.DataFrame(suppliers)
        df = df.rename(columns={
            "supplierid": "ID",
            "suppliername": "Nama Supplier",
            "supplierno": "No. Telepon",
            "address": "Alamat",
            "description": "Deskripsi",
            "products_supplied": "Produk yang Disuplai"
        })

        df['Produk yang Disuplai'] = df['Produk yang Disuplai'].fillna('')

        search_term = st.text_input("Cari berdasarkan Nama Supplier atau Produk yang Disuplai")

        if search_term:
            term = search_term.lower()
            df = df[
                df['Nama Supplier'].str.lower().str.contains(term) |
                df['Produk yang Disuplai'].str.lower().str.contains(term)
            ]
        
        if df.empty:
            st.warning(f"Tidak ada hasil yang cocok dengan pencarian '{search_term}'.")
        else:
            st.data_editor(
                df,
                use_container_width=True,
                hide_index=True,
                disabled=True
            )

    except Exception as e:
        st.error(f"Terjadi kesalahan: {e}")
