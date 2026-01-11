import streamlit as st
from app.db import get_client
import pandas as pd
import datetime

def show():
    st.title("Dashboard Analisis")

    supabase = get_client()

    try:
        # Filter 
        users_resp = supabase.table("users").select("store").neq("role", "admin").execute()
        stores = sorted(list(set([user['store'] for user in users_resp.data])))
        
        if not stores:
            st.info("Belum ada toko yang terdaftar. Buat toko di menu Manajemen Toko & User.")
            return

        col1, col2 = st.columns([0.7, 0.3])
        with col1:
            selected_store = st.selectbox("Pilih Toko untuk Dianalisis", options=stores)
        with col2:
            date_range_option = st.selectbox("Rentang Waktu", 
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
        else: 
            start_date, end_date = st.date_input("Pilih rentang tanggal custom", 
                                                 [today - datetime.timedelta(days=7), today],
                                                 key="custom_date_range")

        st.info(f"Menampilkan analisis untuk **{selected_store}** dari tanggal **{start_date.strftime('%d %b %Y')}** hingga **{end_date.strftime('%d %b %Y')}**.")
        st.markdown("---")

        if selected_store and start_date and end_date:
            # SECTION 1: Business Performance Summary
            st.markdown("<h3 style='color: var(--accent);'>Ringkasan Performa Bisnis</h3>", unsafe_allow_html=True)
            
            try:
                # Get business performance data
                perf_resp = supabase.rpc("get_store_business_performance", {
                    "store_input": selected_store,
                    "start_date": start_date.isoformat(),
                    "end_date": (end_date + datetime.timedelta(days=1)).isoformat()
                }).execute()
                
                perf = perf_resp.data[0] if perf_resp.data else {}
                
                # Modal & HPP
                st.markdown("#### Modal")
                col_m1, col_m2 = st.columns(2)
                with col_m1:
                    total_modal = perf.get('total_modal', 0) or 0
                    st.metric(
                        "Modal (Total Pembelian)", 
                        f"Rp {total_modal:,.0f}",
                        help="Total nilai pembelian barang sepanjang waktu"
                    )
                with col_m2:
                    hpp = perf.get('hpp', 0) or 0
                    st.metric(
                        "HPP (Harga Pokok Penjualan)", 
                        f"Rp {hpp:,.0f}",
                        help="Biaya pokok dari barang yang terjual dalam periode ini"
                    )
                
                st.divider()
                
                # Revenue & Profit
                st.markdown("#### Pendapatan & Laba")
                col_r1, col_r2, col_r3 = st.columns(3)
                with col_r1:
                    total_revenue = perf.get('total_revenue', 0) or 0
                    st.metric(
                        "Laba Kotor ", 
                        f"Rp {total_revenue:,.0f}",
                        help="Total pendapatan dari penjualan"
                    )
                with col_r2:
                    gross_profit = perf.get('gross_profit', 0) or 0
                    st.metric(
                        "Gross Profit", 
                        f"Rp {gross_profit:,.0f}",
                        delta=f"Margin: {(gross_profit/total_revenue*100):.1f}%" if total_revenue > 0 else "0%",
                        help="Laba Kotor = Penjualan - HPP"
                    )
                with col_r3:
                    net_profit = perf.get('net_profit', 0) or 0
                    profit_margin = perf.get('profit_margin', 0) or 0
                    st.metric(
                        "Laba Bersih", 
                        f"Rp {net_profit:,.0f}",
                        delta=f"Margin: {profit_margin:.1f}%",
                        help="Laba Bersih = Gross Profit - Biaya Operasional"
                    )
                
                st.divider()
                
                # Row 3: Expenses
                st.markdown("#### Biaya Operasional")
                col_e1, col_e2, col_e3 = st.columns(3)
                with col_e1:
                    total_expenses = perf.get('total_expenses', 0) or 0
                    st.metric(
                        "Total Biaya", 
                        f"Rp {total_expenses:,.0f}",
                        help="Total biaya operasional dalam periode"
                    )
                with col_e2:
                    salary_expense = perf.get('salary_expense', 0) or 0
                    st.metric(
                        "Gaji Karyawan", 
                        f"Rp {salary_expense:,.0f}",
                        help="Total gaji yang dibayarkan"
                    )
                with col_e3:
                    other_expense = perf.get('other_expense', 0) or 0
                    st.metric(
                        "Biaya Lainnya", 
                        f"Rp {other_expense:,.0f}",
                        help="Biaya operasional selain gaji"
                    )
                
                st.divider()
                
                # Transaction Summary
                st.markdown("#### Ringkasan Transaksi")
                col_t1, col_t2, col_t3 = st.columns(3)
                with col_t1:
                    tx_count = perf.get('transaction_count', 0) or 0
                    st.metric("Jumlah Transaksi", f"{tx_count} transaksi")
                with col_t2:
                    avg_tx = (total_revenue / tx_count) if tx_count > 0 else 0
                    st.metric("Rata-rata Transaksi", f"Rp {avg_tx:,.0f}")
                with col_t3:
                    period_days = (end_date - start_date).days
                    st.metric("Periode Analisis", f"{period_days} hari")
                    
            except Exception as e:
                st.warning(f"Data belum tersedia. SQL ({e})")
                
                # Fallback ke KPI lama
                try:
                    kpis_resp = supabase.rpc("get_store_kpis", {
                        "store_input": selected_store,
                        "start_date": start_date.isoformat(),
                        "end_date": (end_date + datetime.timedelta(days=1)).isoformat()
                    }).execute()
                    
                    kpis = kpis_resp.data
                    
                    total_revenue = kpis.get('total_revenue', 0)
                    total_cost = kpis.get('total_cost', 0)
                    gross_profit = kpis.get('gross_profit', 0)
                    profit_margin = (gross_profit / total_revenue * 100) if total_revenue > 0 else 0
                    
                    kpi_cols = st.columns(4)
                    with kpi_cols[0]:
                        st.metric("Total Pendapatan", f"Rp {total_revenue:,.0f}")
                    with kpi_cols[1]:
                        st.metric("Total Biaya", f"Rp {total_cost:,.0f}")
                    with kpi_cols[2]:
                        st.metric("Laba Kotor", f"Rp {gross_profit:,.0f}")
                    with kpi_cols[3]:
                        st.metric("Margin Laba", f"{profit_margin:.1f}%")
                    
                    trans_cols = st.columns(3)
                    with trans_cols[0]:
                        st.metric("Jumlah Transaksi", f"{kpis.get('sale_count', 0)}")
                    with trans_cols[1]:
                        avg_transaction = (total_revenue / kpis.get('sale_count', 1)) if kpis.get('sale_count', 0) > 0 else 0
                        st.metric("Rata-rata Transaksi", f"Rp {avg_transaction:,.0f}")
                    with trans_cols[2]:
                        st.metric("Periode Analisis", f"{(end_date - start_date).days} hari")
                except:
                    pass

            st.divider()

            # Product Analysis
            st.markdown("<h3 style='color: var(--accent);'>Analisis Produk</h3>", unsafe_allow_html=True)
            
            try:
                top_products_resp = supabase.rpc("get_top_selling_products", {
                    "end_date": (end_date + datetime.timedelta(days=1)).isoformat(),
                    "limit_count": 10,
                    "start_date": start_date.isoformat(),
                    "store_input": selected_store
                }).execute()
                slow_products_resp = supabase.rpc("get_slow_moving_products", {
                    "store_input": selected_store, "days_threshold": 60
                }).execute()

                top_products = top_products_resp.data
                slow_products = slow_products_resp.data
            except:
                top_products = []
                slow_products = []
            
            col_top, col_slow = st.columns(2)
            
            with col_top:
                st.subheader("Produk Terlaris")
                if top_products:
                    df_top = pd.DataFrame(top_products).rename(columns={
                        "product_name": "Nama Produk", 
                        "total_quantity_sold": "Jml Terjual",
                        "total_revenue": "Pendapatan"
                    })
                    df_top['Pendapatan'] = df_top['Pendapatan'].apply(lambda x: f"Rp {x:,.0f}")
                    st.dataframe(df_top[['Nama Produk', 'Jml Terjual', 'Pendapatan']], 
                               use_container_width=True, hide_index=True)
                    
                    chart_data = pd.DataFrame(top_products)
                    if not chart_data.empty:
                        st.bar_chart(chart_data.set_index('product_name')['total_revenue'])
                else:
                    st.info("Tidak ada data penjualan pada rentang tanggal ini.")

            with col_slow:
                st.subheader("Produk Lambat Terjual")
                if slow_products:
                    df_slow = pd.DataFrame(slow_products).rename(columns={
                        "product_name": "Nama Produk", 
                        "last_sale_date": "Terakhir Terjual",
                        "total_stock": "Sisa Stok"
                    })
                    st.dataframe(df_slow[['Nama Produk', 'Terakhir Terjual', 'Sisa Stok']], 
                               use_container_width=True, hide_index=True)
                else:
                    st.success("Tidak ada produk yang lambat terjual.")

            st.divider()
            
            # Expense Breakdown
            st.markdown("<h3 style='color: var(--accent);'>Rincian Biaya Operasional</h3>", unsafe_allow_html=True)
            
            try:
                expense_resp = supabase.rpc("get_expense_summary", {
                    "store_input": selected_store,
                    "start_date": start_date.isoformat(),
                    "end_date": (end_date + datetime.timedelta(days=1)).isoformat()
                }).execute()
                
                expenses = expense_resp.data
                
                if expenses:
                    expense_labels = {
                        'salary': 'Gaji Karyawan',
                        'rent': 'Sewa',
                        'utility': 'Listrik/Air',
                        'maintenance': 'Perawatan',
                        'supplies': 'Perlengkapan',
                        'transport': 'Transportasi',
                        'other': 'Lainnya'
                    }
                    
                    df_expense = pd.DataFrame(expenses)
                    df_expense['expense_type'] = df_expense['expense_type'].map(expense_labels)
                    df_expense = df_expense.rename(columns={
                        'expense_type': 'Jenis Biaya',
                        'total_amount': 'Total',
                        'transaction_count': 'Jumlah'
                    })
                    df_expense['Total'] = df_expense['Total'].apply(lambda x: f"Rp {x:,.0f}")
                    
                    st.dataframe(df_expense, use_container_width=True, hide_index=True)
                else:
                    st.info("Belum ada data biaya operasional untuk periode ini.")
            except Exception as e:
                st.info(f"Data biaya operasional belum tersedia. SQL.")

    except Exception as e:
        st.error(f"Terjadi kesalahan saat memuat dashboard: {e}")
