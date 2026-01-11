import streamlit as st
from app.db import get_client
import pandas as pd
import datetime

def show():
    st.title("Riwayat Stock Adjustment")

    store = st.session_state.get("store")
    if not store:
        st.warning("Toko tidak ditemukan. Silakan login kembali.")
        return

    try:
        supabase = get_client()

        st.subheader("Filter Riwayat")
        
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("Dari Tanggal", value=datetime.date.today() - datetime.timedelta(days=30))
        with col2:
            end_date = st.date_input("Sampai Tanggal", value=datetime.date.today())
        
        search_term = st.text_input("Cari berdasarkan Nama Produk")

        # Data Fetching and Display
        if st.button("Tampilkan Riwayat", type="primary"):
            end_date_param = (end_date + datetime.timedelta(days=1))
            
            response = supabase.rpc("get_stock_adjustment_history", {
                "store_input": store,
                "start_date_input": str(start_date),
                "end_date_input": str(end_date_param)
            }).execute()

            results = response.data
            
            if not results:
                st.info("Tidak ada data penyesuaian stok yang ditemukan untuk periode yang dipilih.")
            else:
                df = pd.DataFrame(results)
                
                if search_term:
                    df = df[df['productname'].str.contains(search_term, case=False, na=False)]

                if df.empty:
                    st.warning(f"Tidak ada hasil yang cocok dengan pencarian '{search_term}'.")
                else:
                    st.write("### Hasil Riwayat:")
                    df = df.rename(columns={
                        "adjustmentid": "ID", "productname": "Produk", "warehouse_name": "Gudang",
                        "quantity": "Jumlah", "adjustment_type": "Tipe", "description": "Deskripsi",
                        "adjusted_at": "Waktu"
                    })
                    
                    df['Waktu'] = pd.to_datetime(df['Waktu']).dt.strftime('%Y-%m-%d %H:%M')

                    st.data_editor(
                        df,
                        use_container_width=True,
                        hide_index=True,
                        disabled=True
                    )

    except Exception as e:
        st.error(f"Terjadi kesalahan: {e}")
