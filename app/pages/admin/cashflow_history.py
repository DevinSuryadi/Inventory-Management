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

        if st.button("Tampilkan Riwayat", type="primary"):
            account_id = account_map[selected_account_label]
            end_date_param = (end_date + datetime.timedelta(days=1))
            
            history_resp = supabase.table("account_transactions").select("*").eq("account_id", account_id).gte("transaction_date", start_date.isoformat()).lt("transaction_date", end_date_param.isoformat()).order("transaction_date", desc=True).execute()
            
            history = history_resp.data
            if not history:
                st.info("Tidak ada transaksi pada periode ini untuk rekening yang dipilih.")
            else:
                df = pd.DataFrame(history)
                
                df['Debit'] = df['amount'].apply(lambda x: x if x > 0 else None)
                df['Kredit'] = df['amount'].apply(lambda x: -x if x < 0 else None)
                
                df = df.rename(columns={
                    "transaction_date": "Tanggal",
                    "description": "Deskripsi",
                    "balance_after": "Saldo Akhir"
                })
                
                df['Tanggal'] = pd.to_datetime(df['Tanggal'], format="mixed").dt.strftime('%Y-%m-%d %H:%M')
                
                for col in ['Debit', 'Kredit', 'Saldo Akhir']:
                    df[col] = df[col].apply(lambda x: f"Rp {x:,.0f}" if pd.notna(x) else "")
                
                st.dataframe(
                    df[['Tanggal', 'Deskripsi', 'Debit', 'Kredit', 'Saldo Akhir']],
                    use_container_width=True,
                    hide_index=True
                )
