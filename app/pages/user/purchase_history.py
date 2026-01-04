import streamlit as st
from app.db import get_client
import pandas as pd
import datetime

def show():
    st.title("Riwayat Pembelian")

    store = st.session_state.get("store")
    if not store:
        st.warning("Sesi toko tidak valid. Silakan login kembali.")
        return

    try:
        supabase = get_client()

        st.subheader("Filter Riwayat Pembelian")
        
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("Dari Tanggal", value=datetime.date.today() - datetime.timedelta(days=30))
        with col2:
            end_date = st.date_input("Sampai Tanggal", value=datetime.date.today())

        search_term = st.text_input("Cari berdasarkan Nama Produk atau Supplier")

        if st.button("Tampilkan Riwayat"):
            end_date_param = (end_date + datetime.timedelta(days=1)).isoformat()
            
            response = supabase.rpc("get_purchase_history", {
                "store_input": store,
                "start_date_input": start_date.isoformat(),
                "end_date_input": end_date_param
            }).execute()

            results = response.data
            
            if not results:
                st.info("Tidak ada riwayat pembelian untuk periode yang dipilih.")
            else:
                df = pd.DataFrame(results)
                
                if search_term:
                    term = search_term.lower()
                    df = df[
                        df['product_name'].str.lower().str.contains(term) |
                        df['supplier_name'].str.lower().str.contains(term)
                    ]

                if df.empty:
                    st.warning(f"Tidak ada riwayat yang cocok dengan pencarian '{search_term}'.")
                else:
                    st.write("### Hasil Riwayat")
                    df = df.rename(columns={
                        "purchaseid": "ID", "product_name": "Produk", "supplier_name": "Supplier",
                        "warehouse_name": "Gudang", "quantity": "Jumlah", "price": "Harga Satuan",
                        "total": "Total Harga", "payment_type": "Pembayaran", "description": "Deskripsi",
                        "purchase_date": "Tanggal"
                    })

                    df['Harga Satuan'] = df['Harga Satuan'].apply(lambda x: f"Rp {x:,.0f}")
                    df['Total Harga'] = df['Total Harga'].apply(lambda x: f"Rp {x:,.0f}")
                    df['Tanggal'] = pd.to_datetime(df['Tanggal']).dt.strftime('%Y-%m-%d %H:%M')

                    st.data_editor(df[[
                        "Tanggal", "Produk", "Supplier", "Jumlah", 
                        "Harga Satuan", "Total Harga", "Pembayaran", "Gudang", "Deskripsi"
                    ]], use_container_width=True, hide_index=True, disabled=True)

    except Exception as e:
        st.error(f"Terjadi kesalahan: {e}")
