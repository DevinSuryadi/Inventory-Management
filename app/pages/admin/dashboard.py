import streamlit as st
from app.db import get_client
import pandas as pd
import datetime

def show():
    st.title("📊Admin Dashboard")
    st.markdown("Pilih toko dan rentang tanggal untuk melihat analisis performa bisnis.")

    supabase = get_client()

    try:
        # --- Bagian 1: Filter ---
        users_resp = supabase.table("users").select("store").neq("role", "admin").execute()
        stores = sorted(list(set([user['store'] for user in users_resp.data])))
        
        if not stores:
            st.info("Belum ada toko yang terdaftar.")
            return

        col1, col2 = st.columns([0.7, 0.3])
        with col1:
            selected_store = st.selectbox("Pilih Toko untuk Dianalisis", options=stores)
        with col2:
            date_range_option = st.selectbox("Pilih Rentang Waktu", 
                                             ["30 Hari Terakhir", "Bulan Ini", "Bulan Lalu", "Custom"])

        today = datetime.date.today()
        if date_range_option == "30 Hari Terakhir":
            start_date = today - datetime.timedelta(days=30)
            end_date = today
        elif date_range_option == "Bulan Ini":
            start_date = today.replace(day=1)
            end_date = today
        elif date_range_option == "Bulan Lalu":
            last_month_end = today.replace(day=1) - datetime.timedelta(days=1)
            start_date = last_month_end.replace(day=1)
            end_date = last_month_end
        else: # Custom
            start_date, end_date = st.date_input("Pilih rentang tanggal custom", 
                                                 [today - datetime.timedelta(days=7), today],
                                                 key="custom_date_range")

        st.info(f"Menampilkan analisis untuk **{selected_store}** dari tanggal **{start_date.strftime('%d %b %Y')}** hingga **{end_date.strftime('%d %b %Y')}**.")
        st.markdown("---")

        if selected_store and start_date and end_date:
            # --- Bagian 2: Tampilan Analisis ---
            
            kpis_resp = supabase.rpc("get_store_kpis", {
                "store_input": selected_store,
                "start_date": start_date.isoformat(),
                "end_date": (end_date + datetime.timedelta(days=1)).isoformat()
            }).execute()
            
            # ... (Panggilan RPC lainnya tetap sama)
            top_products_resp = supabase.rpc("get_top_selling_products", {
                "store_input": selected_store, "start_date": start_date.isoformat(),
                "end_date": (end_date + datetime.timedelta(days=1)).isoformat(), "limit_count": 10
            }).execute()
            slow_products_resp = supabase.rpc("get_slow_moving_products", {
                "store_input": selected_store, "days_threshold": 60
            }).execute()

            kpis = kpis_resp.data
            top_products = top_products_resp.data
            slow_products = slow_products_resp.data

            # PENYEMPURNAAN: Tata Letak KPI Diubah
            st.subheader("Ringkasan Performa Bisnis")
            
            # Baris pertama untuk Pendapatan, Biaya, dan Transaksi
            kpi_row1 = st.columns(3)
            kpi_row1[0].metric("Total Pendapatan", f"Rp {kpis.get('total_revenue', 0):,.0f}")
            kpi_row1[1].metric("Total Biaya (HPP)", f"Rp {kpis.get('total_cost', 0):,.0f}")
            kpi_row1[2].metric("Jumlah Transaksi", f"{kpis.get('sale_count', 0)}")

            # Baris kedua khusus untuk Laba Kotor agar lebih lega
            st.metric("Laba Kotor", f"Rp {kpis.get('gross_profit', 0):,.0f}")

            st.markdown("---")

            # ... (Sisa kode untuk produk terlaris dan lambat terjual tetap sama)
            col_top, col_slow = st.columns(2)
            with col_top:
                st.subheader("Produk Terlaris (Berdasarkan Pendapatan)")
                if top_products:
                    df_top = pd.DataFrame(top_products).rename(columns={
                        "product_name": "Nama Produk", "total_quantity_sold": "Jml Terjual",
                        "total_revenue": "Total Pendapatan"
                    })
                    df_top['Total Pendapatan'] = df_top['Total Pendapatan'].apply(lambda x: f"Rp {x:,.0f}")
                    st.dataframe(df_top, use_container_width=True, hide_index=True)
                    st.bar_chart(pd.DataFrame(top_products), x="product_name", y="total_revenue")
                else:
                    st.info("Tidak ada data penjualan pada rentang tanggal ini.")

            with col_slow:
                st.subheader("Produk Lambat Terjual ")
                if slow_products:
                    df_slow = pd.DataFrame(slow_products).rename(columns={
                        "product_name": "Nama Produk", "last_sale_date": "Terakhir Terjual",
                        "total_stock": "Sisa Stok"
                    })
                    st.dataframe(df_slow, use_container_width=True, hide_index=True)
                else:
                    st.success("Bagus! Tidak ada produk yang lambat terjual.")

    except Exception as e:
        st.error(f"Terjadi kesalahan saat memuat dashboard: {e}")
