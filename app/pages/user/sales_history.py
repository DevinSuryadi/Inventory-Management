import streamlit as st
from app.db import get_client
import pandas as pd
import datetime

def show():
    st.title("Riwayat Penjualan")

    store = st.session_state.get("store")
    if not store:
        st.warning("Sesi toko tidak valid. Silakan login kembali.")
        return

    try:
        supabase = get_client()

        st.subheader("Filter Riwayat Penjualan")
        
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("Dari Tanggal", value=datetime.date.today() - datetime.timedelta(days=30))
        with col2:
            end_date = st.date_input("Sampai Tanggal", value=datetime.date.today())
        
        col_search, col_invoice = st.columns(2)
        with col_search:
            search_term = st.text_input("Cari Nama Produk atau Pelanggan")
        with col_invoice:
            search_invoice = st.text_input("Cari No. Nota")
        
        # Filter jenis penjualan
        sale_type_filter = st.radio("Jenis Penjualan", ["Semua", "Penjualan Stok", "Penjualan Lainnya"], horizontal=True)

        if st.button("Tampilkan Riwayat", type="primary"):
            end_date_param = (end_date + datetime.timedelta(days=1)).isoformat()
            
            response = supabase.rpc("get_sale_history", {
                "store_input": store,
                "start_date_input": start_date.isoformat(),
                "end_date_input": end_date_param
            }).execute()

            results = response.data
            
            if not results:
                st.info("Tidak ada riwayat penjualan untuk periode yang dipilih.")
            else:
                df = pd.DataFrame(results)
                
                if sale_type_filter == "Penjualan Stok":
                    df = df[df.get('is_non_stock', False) == False]
                elif sale_type_filter == "Penjualan Lainnya":
                    df = df[df.get('is_non_stock', False) == True]

                if search_term:
                    term = search_term.lower()
                    df = df[
                        df['product_name'].str.lower().str.contains(term, na=False) |
                        df['customer_name'].str.lower().str.contains(term, na=False)
                    ]
                
                if search_invoice:
                    invoice_term = search_invoice.lower()
                    df = df[df['invoice_number'].str.lower().str.contains(invoice_term, na=False)]

                if df.empty:
                    st.info(f"Tidak ada hasil yang cocok dengan filter yang dipilih.")
                else:
                    st.write("### Hasil Riwayat")
                    
                    rename_cols = {
                        "saleid": "ID", "product_name": "Produk", "warehouse_name": "Gudang",
                        "customer_name": "Pelanggan", "quantity": "Jumlah", "price": "Harga Satuan",
                        "total": "Total Harga", "payment_type": "Pembayaran", "description": "Deskripsi",
                        "sale_date": "Tanggal", "invoice_number": "No. Nota", "is_non_stock": "Jenis"
                    }
                    df = df.rename(columns=rename_cols)

                    df['Harga Satuan'] = df['Harga Satuan'].apply(lambda x: f"Rp {x:,.0f}")
                    df['Total Harga'] = df['Total Harga'].apply(lambda x: f"Rp {x:,.0f}")
                    df['Tanggal'] = pd.to_datetime(df['Tanggal']).dt.strftime('%Y-%m-%d %H:%M')
                    
                    if 'No. Nota' in df.columns:
                        df['No. Nota'] = df['No. Nota'].fillna('-')
                    else:
                        df['No. Nota'] = '-'
                    
                    if 'Jenis' in df.columns:
                        df['Jenis'] = df['Jenis'].apply(lambda x: '📦 Lainnya' if x else '🛒 Stok')
                    else:
                        df['Jenis'] = '🛒 Stok'

                    display_cols = [
                        "Tanggal", "No. Nota", "Produk", "Pelanggan", "Jumlah", 
                        "Harga Satuan", "Total Harga", "Pembayaran", "Gudang", "Jenis", "Deskripsi"
                    ]
                    display_cols = [col for col in display_cols if col in df.columns]
                    
                    st.dataframe(df[display_cols], use_container_width=True)
                    
                    # Summary
                    total_sales = df['Total Harga'].str.replace('Rp ', '').str.replace(',', '').astype(float).sum()
                    st.metric("Total Penjualan", f"Rp {total_sales:,.0f}")

    except Exception as e:
        st.error(f"Terjadi kesalahan: {e}")
