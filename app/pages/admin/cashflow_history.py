import streamlit as st
from app.db import get_client
import pandas as pd
import datetime

def show():
    st.title("Riwayat Arus Kas")
    
    supabase = get_client()

    users_resp = supabase.table("users").select("store").neq("role", "admin").execute()
    stores = sorted(list(set([user['store'] for user in users_resp.data])))
    
    if not stores:
        st.info("Belum ada toko yang terdaftar.")
        return

    selected_store = st.selectbox("Pilih Toko", options=stores)

    if selected_store:
        accounts_resp = supabase.table("accounts").select("*").eq("store", selected_store).order("is_default", desc=True).execute()
        accounts = accounts_resp.data or []
        account_map = {f"{acc['account_name']} (Saldo: Rp {acc['balance']:,.0f})": acc['account_id'] for acc in accounts}

        if not account_map:
            st.warning("Toko ini belum memiliki rekening. Silakan buat di menu Manajemen Keuangan.")
            return

        st.markdown("---")
        st.subheader("Filter Riwayat")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            selected_account_label = st.selectbox("Pilih Rekening", options=account_map.keys())
        with col2:
            start_date = st.date_input("Dari Tanggal", value=datetime.date.today() - datetime.timedelta(days=30))
        with col3:
            end_date = st.date_input("Sampai Tanggal", value=datetime.date.today())
        
        # Filter jenis transaksi
        transaction_types = ["Semua", "Penjualan", "Pembelian", "Retur Penjualan", "Retur Pembelian", 
                          "Pembayaran Hutang", "Penerimaan Piutang", "Gaji", "Biaya Operasional", 
                          "Penyesuaian", "Lainnya"]
        selected_type = st.selectbox("Jenis Transaksi", options=transaction_types)

        if st.button("Tampilkan Riwayat", type="primary"):
            account_id = account_map[selected_account_label]
            end_date_param = (end_date + datetime.timedelta(days=1))
            
            history_resp = supabase.table("account_transactions").select("*").eq("account_id", account_id).gte("transaction_date", start_date.isoformat()).lt("transaction_date", end_date_param.isoformat()).order("transaction_date", desc=True).execute()
            
            history = history_resp.data
            if not history:
                st.info("Tidak ada transaksi pada periode ini untuk rekening yang dipilih.")
            else:
                df = pd.DataFrame(history)
                
                # Extract No. Nota 
                def extract_nota(desc):
                    if not desc:
                        return '-'
                    if '(Nota:' in desc:
                        try:
                            start = desc.index('(Nota:') + 7
                            end = desc.index(')', start)
                            return desc[start:end].strip()
                        except:
                            return '-'
                    return '-'
                
                df['No. Nota'] = df['description'].apply(extract_nota)
                
                # Filter transaction type
                if selected_type != "Semua":
                    type_mapping = {
                        "Penjualan": ["sale", "other_sale"],
                        "Pembelian": ["purchase", "other_purchase"],
                        "Retur Penjualan": ["sale_return"],
                        "Retur Pembelian": ["purchase_return"],
                        "Pembayaran Hutang": ["debt_payment"],
                        "Penerimaan Piutang": ["receivable_payment"],
                        "Gaji": ["salary"],
                        "Biaya Operasional": ["expense", "operational_expense"],
                        "Penyesuaian": ["adjustment", "cash_adjustment"],
                        "Lainnya": ["other", "transfer"]
                    }
                    filter_types = type_mapping.get(selected_type, [])
                    if filter_types:
                        df = df[df['transaction_type'].isin(filter_types)]
                
                if df.empty:
                    st.info(f"Tidak ada transaksi {selected_type} pada periode ini.")
                else:
                    def get_type_label(tx_type):
                        type_labels = {
                            "sale": "Penjualan",
                            "other_sale": "Penjualan Lainnya",
                            "purchase": "Pembelian",
                            "other_purchase": "Pembelian Lainnya",
                            "sale_return": "Retur Penjualan",
                            "purchase_return": "Retur Pembelian",
                            "debt_payment": "Pembayaran Hutang",
                            "receivable_payment": "Penerimaan Piutang",
                            "salary": "Gaji Karyawan",
                            "expense": "Biaya Operasional",
                            "operational_expense": "Biaya Operasional",
                            "adjustment": "Penyesuaian",
                            "cash_adjustment": "Penyesuaian Kas",
                            "transfer": "Transfer",
                            "other": "Lainnya"
                        }
                        return type_labels.get(tx_type, f"{tx_type}")
                    
                    df['Jenis'] = df['transaction_type'].apply(get_type_label)
                    
                    df['Debit'] = df['amount'].apply(lambda x: x if x > 0 else None)
                    df['Kredit'] = df['amount'].apply(lambda x: -x if x < 0 else None)
                    
                    df = df.rename(columns={
                        "transaction_date": "Tanggal",
                        "description": "Keterangan",
                        "balance_after": "Saldo Akhir"
                    })
                    
                    df['Tanggal'] = pd.to_datetime(df['Tanggal'], format="mixed").dt.strftime('%Y-%m-%d %H:%M')
                    
                    for col in ['Debit', 'Kredit', 'Saldo Akhir']:
                        df[col] = df[col].apply(lambda x: f"Rp {x:,.0f}" if pd.notna(x) else "")
                    
                    st.dataframe(
                        df[['Tanggal', 'Jenis', 'No. Nota', 'Keterangan', 'Debit', 'Kredit', 'Saldo Akhir']],
                        use_container_width=True,
                        hide_index=True
                    )
                    
                    # Summary
                    total_debit = df['Debit'].apply(lambda x: float(x.replace('Rp ', '').replace(',', '')) if x else 0).sum()
                    total_kredit = df['Kredit'].apply(lambda x: float(x.replace('Rp ', '').replace(',', '')) if x else 0).sum()
                    
                    col_summary1, col_summary2, col_summary3 = st.columns(3)
                    with col_summary1:
                        st.metric("Total Debit (Masuk)", f"Rp {total_debit:,.0f}")
                    with col_summary2:
                        st.metric("Total Kredit (Keluar)", f"Rp {total_kredit:,.0f}")
                    with col_summary3:
                        st.metric("Net Arus Kas", f"Rp {total_debit - total_kredit:,.0f}")
