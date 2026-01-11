import streamlit as st
from app.db import get_client
import pandas as pd
import datetime

def show():
    st.title("Riwayat Retur")

    store = st.session_state.get("store")
    if not store:
        st.warning("Sesi toko tidak valid. Silakan login kembali.")
        return

    try:
        supabase = get_client()

        tab1, tab2 = st.tabs(["Retur Pembelian", "Retur Penjualan"])

        # Purchase Return History
        with tab1:
            st.subheader("Riwayat Retur Pembelian")
            
            col1, col2 = st.columns(2)
            with col1:
                start_date_pr = st.date_input("Dari Tanggal", value=datetime.date.today() - datetime.timedelta(days=30), key="pr_start")
            with col2:
                end_date_pr = st.date_input("Sampai Tanggal", value=datetime.date.today(), key="pr_end")

            if st.button("Tampilkan Riwayat Retur Pembelian", key="btn_pr", type="primary"):
                try:
                    response = supabase.rpc("get_purchase_return_history", {
                        "store_input": store,
                        "start_date_input": start_date_pr.isoformat(),
                        "end_date_input": (end_date_pr + datetime.timedelta(days=1)).isoformat()
                    }).execute()

                    results = response.data
                    
                    if not results:
                        st.info("Tidak ada riwayat retur pembelian untuk periode yang dipilih.")
                    else:
                        df = pd.DataFrame(results)
                        df = df.rename(columns={
                            "return_id": "ID",
                            "supplier_name": "Supplier",
                            "warehouse_name": "Gudang",
                            "total_amount": "Total",
                            "return_type": "Jenis",
                            "status": "Status",
                            "reason": "Alasan",
                            "return_date": "Tanggal",
                            "item_count": "Jml Item"
                        })
                        
                        df['Total'] = df['Total'].apply(lambda x: f"Rp {x:,.0f}")
                        df['Tanggal'] = pd.to_datetime(df['Tanggal']).dt.strftime('%Y-%m-%d %H:%M')
                        df['Jenis'] = df['Jenis'].map({
                            'refund': 'Refund',
                            'replacement': 'Tukar',
                            'credit_note': 'Credit Note'
                        })
                        df['Status'] = df['Status'].map({
                            'pending': 'Pending',
                            'approved': 'Approved',
                            'completed': 'Selesai',
                            'rejected': 'Ditolak'
                        })
                        
                        st.dataframe(
                            df[['ID', 'Tanggal', 'Supplier', 'Gudang', 'Jml Item', 'Total', 'Jenis', 'Status', 'Alasan']],
                            use_container_width=True,
                            hide_index=True
                        )
                        
                        # Summary
                        st.markdown("---")
                        col_s1, col_s2, col_s3 = st.columns(3)
                        with col_s1:
                            st.metric("Total Retur", len(results))
                        with col_s2:
                            total_value = sum([r['total_amount'] for r in results])
                            st.metric("Total Nilai", f"Rp {total_value:,.0f}")
                        with col_s3:
                            total_items = sum([r['item_count'] for r in results])
                            st.metric("Total Item", total_items)
                            
                except Exception as e:
                    st.error(f"Gagal memuat riwayat: {e}")

        # Sale Return History
        with tab2:
            st.subheader("Riwayat Retur Penjualan")
            
            col1, col2 = st.columns(2)
            with col1:
                start_date_sr = st.date_input("Dari Tanggal", value=datetime.date.today() - datetime.timedelta(days=30), key="sr_start")
            with col2:
                end_date_sr = st.date_input("Sampai Tanggal", value=datetime.date.today(), key="sr_end")

            if st.button("Tampilkan Riwayat Retur Penjualan", key="btn_sr", type="primary"):
                try:
                    response = supabase.rpc("get_sale_return_history", {
                        "store_input": store,
                        "start_date_input": start_date_sr.isoformat(),
                        "end_date_input": (end_date_sr + datetime.timedelta(days=1)).isoformat()
                    }).execute()

                    results = response.data
                    
                    if not results:
                        st.info("Tidak ada riwayat retur penjualan untuk periode yang dipilih.")
                    else:
                        df = pd.DataFrame(results)
                        df = df.rename(columns={
                            "return_id": "ID",
                            "customer_name": "Pelanggan",
                            "warehouse_name": "Gudang",
                            "total_amount": "Total",
                            "return_type": "Jenis",
                            "status": "Status",
                            "reason": "Alasan",
                            "return_date": "Tanggal",
                            "item_count": "Jml Item"
                        })
                        
                        df['Total'] = df['Total'].apply(lambda x: f"Rp {x:,.0f}")
                        df['Tanggal'] = pd.to_datetime(df['Tanggal']).dt.strftime('%Y-%m-%d %H:%M')
                        df['Pelanggan'] = df['Pelanggan'].fillna('Tanpa Nama')
                        df['Jenis'] = df['Jenis'].map({
                            'refund': 'Refund',
                            'replacement': 'Tukar',
                            'store_credit': 'Store Credit'
                        })
                        df['Status'] = df['Status'].map({
                            'pending': 'Pending',
                            'approved': 'Approved',
                            'completed': 'Selesai',
                            'rejected': 'Ditolak'
                        })
                        
                        st.dataframe(
                            df[['ID', 'Tanggal', 'Pelanggan', 'Gudang', 'Jml Item', 'Total', 'Jenis', 'Status', 'Alasan']],
                            use_container_width=True,
                            hide_index=True
                        )
                        
                        # Summary
                        st.markdown("---")
                        col_s1, col_s2, col_s3 = st.columns(3)
                        with col_s1:
                            st.metric("Total Retur", len(results))
                        with col_s2:
                            total_value = sum([r['total_amount'] for r in results])
                            st.metric("Total Nilai", f"Rp {total_value:,.0f}")
                        with col_s3:
                            total_items = sum([r['item_count'] for r in results])
                            st.metric("Total Item", total_items)
                            
                except Exception as e:
                    st.error(f"Gagal memuat riwayat: {e}")

    except Exception as e:
        st.error(f"Terjadi kesalahan: {e}")
