import streamlit as st
from app.db import get_client
import pandas as pd
import datetime

def show():
    st.title("Manajemen Utang ke Supplier")

    store = st.session_state.get("store")
    if not store:
        st.warning("Sesi toko tidak valid. Silakan login kembali.")
        return

    supabase = get_client()

    tab1, tab2 = st.tabs(["Utang Aktif", "Riwayat Utang Lunas"])

    # Utang Aktif
    with tab1:
        st.header("Daftar Utang yang Belum Lunas")
        try:
            active_debts_resp = supabase.rpc("get_supplier_debts", {"store_input": store}).execute()
            active_debts = active_debts_resp.data

            if not active_debts:
                st.info("Tidak ada utang aktif kepada supplier. Bagus!")
            else:
                df_active = pd.DataFrame(active_debts)
                
                search_term_active = st.text_input("Cari utang aktif berdasarkan nama supplier", key="search_active")
                if search_term_active:
                    df_active = df_active[df_active['supplier_name'].str.contains(search_term_active, case=False, na=False)]

                if df_active.empty:
                    st.warning("Tidak ada utang aktif yang cocok dengan pencarian Anda.")
                else:
                    st.write(f"Menampilkan {len(df_active)} utang aktif.")
                    
                    for index, row in df_active.iterrows():
                        sisa_utang = row['remaining_debt']
                        with st.expander(f"Utang ke **{row['supplier_name']}** - Sisa: Rp {sisa_utang:,.0f}"):
                            st.write(f"**ID Utang:** {row['debtid']}")
                            st.write(f"**Tanggal Utang:** {pd.to_datetime(row['debt_date']).strftime('%d %B %Y')}")
                            st.write(f"**Total Utang:** Rp {row['total_debt']:,.0f}")
                            st.write(f"**Sudah Dibayar:** Rp {row['paid_amount']:,.0f}")
                            st.write(f"**Deskripsi:** {row['purchase_description'] or '-'}")
                            
                            with st.form(f"payment_form_supplier_{row['debtid']}"):
                                st.write("**Form Pembayaran**")

                                # Input Tanggal dan Waktu
                                col_tgl, col_jam = st.columns(2)
                                with col_tgl:
                                    payment_date = st.date_input("Tanggal Bayar", value=datetime.date.today())
                                with col_jam:
                                    payment_time = st.time_input("Waktu Bayar", value=datetime.datetime.now().time())

                                payment_amount = st.number_input("Jumlah Pembayaran (Rp)", min_value=0, max_value=int(sisa_utang), step=1000, format="%d")
                                payment_note = st.text_area("Catatan Pembayaran", value="Pembayaran utang supplier")
                                
                                if st.form_submit_button("Bayar"):
                                    payment_datetime = datetime.datetime.combine(payment_date, payment_time)
                                    supabase.rpc("record_supplier_payment", {
                                        "p_debtid": row['debtid'],
                                        "p_amount": payment_amount,
                                        "p_note": payment_note,
                                        "p_transaction_date": payment_datetime.isoformat() # Kirim tanggal manual
                                    }).execute()
                                    st.success("Pembayaran berhasil dicatat!")
                                    st.rerun()
                            
                            st.write("**Riwayat Pembayaran Utang Ini:**")
                            history_resp = supabase.table("payment_history").select("*").eq("debtid", row['debtid']).order("paidat", desc=True).execute()
                            if history_resp.data:
                                df_hist = pd.DataFrame(history_resp.data)[['paidat', 'paidamount', 'description']].rename(columns={'paidat': 'Tgl Bayar', 'paidamount': 'Jumlah', 'description': 'Catatan'})
                                df_hist['Jumlah'] = df_hist['Jumlah'].apply(lambda x: f"Rp {x:,.0f}")
                                df_hist['Tgl Bayar'] = pd.to_datetime(df_hist['Tgl Bayar']).dt.strftime('%Y-%m-%d %H:%M')
                                st.dataframe(df_hist, use_container_width=True, hide_index=True)
                            else:
                                st.info("Belum ada riwayat pembayaran.")

        except Exception as e:
            st.error(f"Terjadi kesalahan saat memuat utang aktif: {e}")

    # Riwayat Utang Lunas
    with tab2:
        st.header("Riwayat Utang yang Telah Lunas")
        try:
            paid_debts_resp = supabase.rpc("get_paid_supplier_debts_with_history", {"store_input": store}).execute()
            paid_debts = paid_debts_resp.data
            if not paid_debts:
                st.info("Belum ada riwayat utang yang lunas.")
            else:
                df_paid = pd.DataFrame(paid_debts)
                search_term_paid = st.text_input("Cari riwayat berdasarkan nama supplier", key="search_paid")
                if search_term_paid:
                    df_paid = df_paid[df_paid['supplier_name'].str.contains(search_term_paid, case=False, na=False)]
                if df_paid.empty:
                    st.warning("Tidak ada riwayat yang cocok dengan pencarian Anda.")
                else:
                    st.write(f"Menampilkan {len(df_paid)} riwayat utang lunas.")
                    for index, row in df_paid.iterrows():
                        with st.expander(f"Lunas: Utang ke **{row['supplier_name']}** - Total Rp {row['total_debt']:,.0f}"):
                            st.write(f"**ID Utang:** {row['debtid']}")
                            st.write(f"**Tanggal Utang:** {pd.to_datetime(row['debt_date']).strftime('%d %B %Y')}")
                            st.write(f"**Deskripsi:** {row['purchase_description'] or '-'}")
                            
                            # Fetch detail produk yang dibeli dalam transaksi ini
                            try:
                                purchase_details = supabase.table("purchase").select(
                                    "product(productname), quantity, harga_satuan"
                                ).eq("debtid", row['debtid']).execute()
                                
                                if purchase_details.data:
                                    st.markdown("---")
                                    st.write("**Produk yang Dibeli:**")
                                    for item in purchase_details.data:
                                        product_name = item['product'][0]['productname'] if item['product'] else "Produk tidak ditemukan"
                                        qty = item['quantity']
                                        price = item['harga_satuan']
                                        total = qty * price
                                        st.write(f"- {product_name}: {qty} unit @ Rp {price:,.0f} = Rp {total:,.0f}")
                            except Exception as e:
                                st.warning(f"Tidak dapat memuat detail produk: {str(e)}")
                            
                            st.markdown("---")
                            st.write("**Detail Pelunasan (Cicilan):**")
                            st.text(row['payment_history_details'] or 'Tidak ada detail pembayaran tercatat.')
        except Exception as e:
            st.error(f"Terjadi kesalahan saat memuat riwayat utang: {e}")
