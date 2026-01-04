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
        try:
            active_debts_resp = supabase.rpc("get_customer_debts", {"store_input": store}).execute()
            active_debts = active_debts_resp.data

            if not active_debts:
                st.info("Tidak ada piutang pelanggan yang aktif. Kerja bagus!")
            else:
                df_active = pd.DataFrame(active_debts)
                
                search_term_active = st.text_input("Cari piutang aktif berdasarkan nama pelanggan", key="search_active_customer")
                if search_term_active:
                    df_active = df_active[df_active['customer_name'].str.contains(search_term_active, case=False, na=False)]

                if df_active.empty:
                    st.warning("Tidak ada piutang aktif yang cocok dengan pencarian Anda.")
                else:
                    st.write(f"Menampilkan {len(df_active)} piutang aktif.")
                    
                    for index, row in df_active.iterrows():
                        sisa_piutang = row['remaining_debt']
                        with st.expander(f"Piutang dari **{row['customer_name'] or 'Tanpa Nama'}** - Sisa: Rp {sisa_piutang:,.0f}"):
                            st.write(f"**ID Piutang:** {row['debtid']}")
                            st.write(f"**Tanggal Transaksi:** {pd.to_datetime(row['debt_date']).strftime('%d %B %Y')}")
                            st.write(f"**Total Piutang:** Rp {row['total_debt']:,.0f}")
                            st.write(f"**Sudah Dibayar:** Rp {row['paid_amount']:,.0f}")
                            st.write(f"**Deskripsi:** {row['sale_description'] or '-'}")
                            
                            # Fetch detail produk yang terjual dalam transaksi ini
                            try:
                                sale_details = supabase.table("sale").select(
                                    "product(productname, type), quantity, price"
                                ).eq("saleid", row['debtid']).execute()
                                
                                if sale_details.data:
                                    st.markdown("---")
                                    st.write("**Produk yang Terjual:**")
                                    for item in sale_details.data:
                                        product = item.get('product')
                                        if isinstance(product, list) and len(product) > 0:
                                            product_name = product[0].get('productname', 'Produk tidak ditemukan')
                                            product_type = product[0].get('type', '-')
                                        else:
                                            product_name = 'Produk tidak ditemukan'
                                            product_type = '-'
                                        qty = item.get('quantity', 0)
                                        price = item.get('price', 0)
                                        st.write(f"- {product_name} ({product_type}): {qty} unit @ Rp {price:,.0f} = Rp {qty * price:,.0f}")
                            except Exception as e:
                                st.warning("Produk detail tidak tersedia")
                            
                            st.markdown("---")
                            
                            with st.form(f"payment_form_customer_{row['debtid']}"):
                                st.write("**Form Pembayaran**")

                                # Input Tanggal dan Waktu
                                col_tgl, col_jam = st.columns(2)
                                with col_tgl:
                                    payment_date = st.date_input("Tanggal Bayar", value=datetime.date.today(), key=f"pay_date_{row['debtid']}_1")
                                with col_jam:
                                    payment_time = st.time_input("Waktu Bayar", value=datetime.datetime.now().time(), key=f"pay_time_{row['debtid']}_1")

                                payment_amount = st.number_input("Jumlah Pembayaran (Rp)", min_value=0, max_value=int(sisa_piutang), step=1000, format="%d", key=f"pay_amt_{row['debtid']}_1")
                                payment_note = st.text_area("Catatan Pembayaran", value="Pembayaran piutang pelanggan", key=f"pay_note_{row['debtid']}_1")
                                
                                if st.form_submit_button("Terima Pembayaran"):
                                    payment_datetime = datetime.datetime.combine(payment_date, payment_time)
                                    supabase.rpc("record_customer_payment", {
                                        "p_debtid": row['debtid'],
                                        "p_amount": payment_amount,
                                        "p_note": payment_note,
                                        "p_transaction_date": payment_datetime.isoformat()
                                    }).execute()
                                    st.success("Pembayaran berhasil dicatat!")
                                    st.rerun()
                            
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
                search_term_paid = st.text_input("Cari riwayat berdasarkan nama pelanggan", key="search_paid_customer")
                if search_term_paid:
                    df_paid = df_paid[df_paid['customer_name'].str.contains(search_term_paid, case=False, na=False)]
                if df_paid.empty:
                    st.warning("Tidak ada riwayat yang cocok dengan pencarian Anda.")
                else:
                    st.write(f"Menampilkan {len(df_paid)} riwayat piutang lunas.")
                    for index, row in df_paid.iterrows():
                        with st.expander(f"Lunas: Piutang dari **{row['customer_name'] or 'Tanpa Nama'}** - Total Rp {row['total_debt']:,.0f}"):
                            st.write(f"**ID Piutang:** {row['debtid']}")
                            st.write(f"**Tanggal Transaksi:** {pd.to_datetime(row['debt_date']).strftime('%d %B %Y')}")
                            st.write(f"**Deskripsi:** {row['sale_description'] or '-'}")
                            
                            # Fetch detail produk yang terjual dalam transaksi ini
                            try:
                                sale_details = supabase.table("sale").select(
                                    "product(productname, type), quantity"
                                ).eq("saleid", row['debtid']).execute()
                                
                                if sale_details.data:
                                    st.markdown("---")
                                    st.write("**Produk yang Terjual:**")
                                    for item in sale_details.data:
                                        product = item.get('product')
                                        if isinstance(product, list) and len(product) > 0:
                                            product_name = product[0].get('productname', 'Produk tidak ditemukan')
                                            product_type = product[0].get('type', '-')
                                        else:
                                            product_name = 'Produk tidak ditemukan'
                                            product_type = '-'
                                        qty = item.get('quantity', 0)
                                        st.write(f"- {product_name} ({product_type}): {qty} unit")
                            except Exception as e:
                                pass  # Silently skip if sale data not available
                            
                            st.markdown("---")
                            st.write("**Detail Pelunasan (Cicilan):**")
                            st.text(row['payment_history_details'] or 'Tidak ada detail pembayaran tercatat.')
        except Exception as e:
            st.error(f"Terjadi kesalahan saat memuat riwayat piutang: {e}")
