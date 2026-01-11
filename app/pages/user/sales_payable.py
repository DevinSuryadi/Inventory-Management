import streamlit as st
from app.db import get_client
import pandas as pd
import datetime

def show():
    st.title("Manajemen Piutang Pelanggan")

    store = st.session_state.get("store")
    if not store:
        st.warning("Sesi toko tidak valid. Silakan login kembali.")
        return

    supabase = get_client()

    tab1, tab2 = st.tabs(["Piutang Aktif", "Riwayat Piutang Lunas"])

    # Piutang Aktif 
    with tab1:
        st.header("Daftar Piutang yang Belum Lunas")
        
        # Sort options
        col_sort, col_filter = st.columns(2)
        with col_sort:
            sort_option = st.selectbox(
                "Urutkan berdasarkan",
                options=["due_date_asc", "due_date_desc", "amount_desc", "date_desc"],
                format_func=lambda x: {
                    "due_date_asc": "Jatuh Tempo Terdekat",
                    "due_date_desc": "Jatuh Tempo Terjauh",
                    "amount_desc": "Jumlah Terbesar",
                    "date_desc": "Tanggal Terbaru"
                }.get(x, x),
                key="sort_customer_debt"
            )
        with col_filter:
            show_overdue_only = st.checkbox("Tampilkan hanya jatuh tempo", key="filter_overdue_cust")
        
        try:
            # Try new function with TOP first
            try:
                active_debts_resp = supabase.rpc("get_customer_debts_with_top", {"store_input": store}).execute()
                active_debts = active_debts_resp.data
                has_top = True
            except:
                # Fallback to old function
                active_debts_resp = supabase.rpc("get_customer_debts", {"store_input": store}).execute()
                active_debts = active_debts_resp.data
                has_top = False

            if not active_debts:
                st.success("Tidak ada piutang pelanggan aktif")
            else:
                df_active = pd.DataFrame(active_debts)
                
                # Apply sorting
                if has_top and 'due_date' in df_active.columns:
                    if sort_option == "due_date_asc":
                        df_active = df_active.sort_values('due_date', ascending=True, na_position='last')
                    elif sort_option == "due_date_desc":
                        df_active = df_active.sort_values('due_date', ascending=False, na_position='last')
                
                if sort_option == "amount_desc":
                    df_active = df_active.sort_values('remaining_debt', ascending=False)
                elif sort_option == "date_desc":
                    df_active = df_active.sort_values('debt_date', ascending=False)
                
                # Filter overdue
                if show_overdue_only and has_top and 'days_until_due' in df_active.columns:
                    df_active = df_active[df_active['days_until_due'] < 0]
                
                search_term_active = st.text_input("🔍 Cari berdasarkan nama pelanggan", key="search_active_customer")
                if search_term_active:
                    df_active = df_active[df_active['customer_name'].str.contains(search_term_active, case=False, na=False)]

                if df_active.empty:
                    st.warning("Tidak ada piutang aktif yang cocok dengan filter/pencarian.")
                else:
                    # Summary metrics
                    col_m1, col_m2, col_m3 = st.columns(3)
                    with col_m1:
                        total_debt = df_active['remaining_debt'].sum()
                        st.metric("Total Piutang", f"Rp {total_debt:,.0f}")
                    with col_m2:
                        st.metric("Jumlah Tagihan", f"{len(df_active)} pelanggan")
                    with col_m3:
                        if has_top and 'days_until_due' in df_active.columns:
                            overdue_count = len(df_active[df_active['days_until_due'] < 0])
                            st.metric("Jatuh Tempo", f"{overdue_count} tagihan", delta="-overdue" if overdue_count > 0 else None, delta_color="inverse")
                    
                    st.divider()
                    st.write(f"Menampilkan {len(df_active)} piutang aktif.")
                    
                    for index, row in df_active.iterrows():
                        sisa_piutang = row['remaining_debt']
                        customer = row.get('customer_name') or 'Tanpa Nama'
                        
                        # Determine urgency badge
                        urgency_badge = ""
                        if has_top and 'days_until_due' in row and row['days_until_due'] is not None:
                            days = row['days_until_due']
                            if days < 0:
                                urgency_badge = f"Jatuh Tempo{abs(int(days))} Hari lalu"
                            elif days <= 7:
                                urgency_badge = f"{int(days)} Hari lagi"
                            elif days <= 30:
                                urgency_badge = f"{int(days)} Hari lagi"
                        
                        with st.expander(f"**{customer}** - Sisa: Rp {sisa_piutang:,.0f} {urgency_badge}"):
                            col_info1, col_info2 = st.columns(2)
                            with col_info1:
                                st.write(f"**ID Piutang:** {row['debtid']}")
                                st.write(f"**Tanggal Transaksi:** {pd.to_datetime(row['debt_date']).strftime('%d %B %Y')}")
                                st.write(f"**Total Piutang:** Rp {row['total_debt']:,.0f}")
                            with col_info2:
                                st.write(f"**Sudah Dibayar:** Rp {row['paid_amount']:,.0f}")
                                if has_top and row.get('due_date'):
                                    st.write(f"**Jatuh Tempo (TOP):** {pd.to_datetime(row['due_date']).strftime('%d %B %Y')}")
                                st.write(f"**Deskripsi:** {row.get('sale_description') or '-'}")
                            
                            st.markdown("---")
                            
                            with st.form(f"payment_form_customer_{row['debtid']}"):
                                st.write("**Form Pembayaran**")

                                col_tgl, col_jam = st.columns(2)
                                with col_tgl:
                                    payment_date = st.date_input("Tanggal Bayar", value=datetime.date.today(), key=f"pay_date_{row['debtid']}_1")
                                with col_jam:
                                    payment_time = st.time_input("Waktu Bayar", value=datetime.datetime.now().time(), key=f"pay_time_{row['debtid']}_1")

                                payment_amount = st.number_input("Jumlah Pembayaran (Rp)", min_value=0, max_value=int(sisa_piutang), step=1000, format="%d", key=f"pay_amt_{row['debtid']}_1")
                                payment_note = st.text_area("Catatan Pembayaran", value="Pembayaran piutang pelanggan", key=f"pay_note_{row['debtid']}_1")
                                
                                confirm = st.checkbox("Konfirmasi penerimaan pembayaran", key=f"confirm_cust_{row['debtid']}")
                                
                                submitted = st.form_submit_button("Terima Pembayaran")
                                
                                if submitted:
                                    if not confirm:
                                        st.error("Harap centang konfirmasi terlebih dahulu!")
                                    else:
                                        payment_datetime = datetime.datetime.combine(payment_date, payment_time)
                                        try:
                                            supabase.rpc("record_customer_payment", {
                                                "p_debtid": row['debtid'],
                                                "p_amount": payment_amount,
                                                "p_note": payment_note,
                                                "p_transaction_date": payment_datetime.isoformat()
                                            }).execute()
                                            st.success("✅ Pembayaran berhasil dicatat!")
                                            st.rerun()
                                        except Exception as e:
                                            st.error(f"Gagal mencatat pembayaran: {e}")
                            
                            st.write("**Riwayat Pembayaran Piutang Ini:**")
                            history_resp = supabase.table("payment_history").select("*").eq("debtid", row['debtid']).order("paidat", desc=True).execute()
                            if history_resp.data:
                                df_hist = pd.DataFrame(history_resp.data)[['paidat', 'paidamount', 'description']].rename(columns={'paidat': 'Tgl Bayar', 'paidamount': 'Jumlah', 'description': 'Catatan'})
                                df_hist['Jumlah'] = df_hist['Jumlah'].apply(lambda x: f"Rp {x:,.0f}")
                                df_hist['Tgl Bayar'] = pd.to_datetime(df_hist['Tgl Bayar']).dt.strftime('%Y-%m-%d %H:%M')
                                st.dataframe(df_hist, use_container_width=True, hide_index=True)
                            else:
                                st.info("Belum ada riwayat pembayaran.")

        except Exception as e:
            st.error(f"Terjadi kesalahan saat memuat piutang aktif: {e}")

    # Riwayat Piutang Lunas
    with tab2:
        st.header("Riwayat Piutang yang Telah Lunas")
        try:
            paid_debts_resp = supabase.rpc("get_paid_customer_debts_with_history", {"store_input": store}).execute()
            paid_debts = paid_debts_resp.data
            if not paid_debts:
                st.info("Belum ada riwayat piutang yang lunas.")
            else:
                df_paid = pd.DataFrame(paid_debts)
                search_term_paid = st.text_input("Cari berdasarkan nama pelanggan", key="search_paid_customer")
                if search_term_paid:
                    df_paid = df_paid[df_paid['customer_name'].str.contains(search_term_paid, case=False, na=False)]
                if df_paid.empty:
                    st.warning("Tidak ada riwayat yang cocok dengan pencarian Anda.")
                else:
                    st.write(f"Menampilkan {len(df_paid)} riwayat piutang lunas.")
                    for index, row in df_paid.iterrows():
                        customer = row.get('customer_name') or 'Tanpa Nama'
                        with st.expander(f"✅ **{customer}** - Total Rp {row['total_debt']:,.0f}"):
                            st.write(f"**ID Piutang:** {row['debtid']}")
                            st.write(f"**Tanggal Transaksi:** {pd.to_datetime(row['debt_date']).strftime('%d %B %Y')}")
                            st.write(f"**Deskripsi:** {row.get('sale_description') or '-'}")
                            st.markdown("---")
                            st.write("**Detail Pelunasan (Cicilan):**")
                            st.text(row.get('payment_history_details') or 'Tidak ada detail pembayaran tercatat.')
        except Exception as e:
            st.error(f"Terjadi kesalahan saat memuat riwayat piutang: {e}")
