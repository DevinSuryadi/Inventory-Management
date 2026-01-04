import streamlit as st
from app.db import get_client
import pandas as pd
import datetime

def show():
    st.title("Manajemen Keuangan Toko")
    
    supabase = get_client()
    admin_user = st.session_state.get("username")

    # Ambil daftar toko
    users_resp = supabase.table("users").select("store").neq("role", "admin").execute()
    stores = sorted(list(set([user['store'] for user in users_resp.data])))
    
    if not stores:
        st.info("Belum ada toko yang terdaftar.")
        return

    selected_store = st.selectbox("Pilih Toko untuk Dikelola", options=stores)

    if selected_store:
        # Pastikan toko punya akun kas default
        supabase.rpc("create_default_cash_account", {"p_store_name": selected_store}).execute()
        
        # Ambil semua akun untuk toko yang dipilih
        accounts_resp = supabase.table("accounts").select("*").eq("store", selected_store).order("is_default", desc=True).execute()
        accounts = accounts_resp.data or []
        account_map = {f"{acc['account_name']} ({acc['account_type']})": acc for acc in accounts}

        st.markdown("---")
        st.subheader("Ringkasan Saldo")
        
        # Tampilkan saldo dalam kolom
        cols = st.columns(len(accounts))
        for i, acc in enumerate(accounts):
            cols[i].metric(label=acc['account_name'], value=f"Rp {acc['balance']:,.0f}")

        st.markdown("---")
        
        tab1, tab2, tab3 = st.tabs(["Tambah Rekening Bank", "Penyesuaian Saldo", "Transfer Dana"])

        with tab1:
            st.subheader("Daftarkan Rekening Bank Baru")
            with st.form("add_bank_account_form"):
                bank_name = st.text_input("Nama Bank (e.g., BCA, Mandiri)")
                account_name = st.text_input("Nama Rekening (e.g., BCA Operasional)")
                account_number = st.text_input("Nomor Rekening")
                submitted = st.form_submit_button("Simpan Rekening")
                if submitted:
                    try:
                        response = supabase.table("accounts").insert({
                            "store": selected_store,
                            "account_name": account_name,
                            "account_type": "bank",
                            "bank_name": bank_name,
                            "account_number": account_number
                        }).execute()
                        
                        if response.data:
                            st.success("Rekening bank berhasil ditambahkan!")
                            st.rerun()
                        else:
                            st.error("Gagal menambahkan rekening. Silakan coba lagi.")
                    except Exception as e:
                        error_str = str(e)
                        if "duplicate key" in error_str.lower() or "unique constraint" in error_str.lower():
                            st.error(f"Rekening '{account_name}' sudah terdaftar di toko ini. Gunakan nama lain.")
                        else:
                            st.error(f"Gagal menambahkan rekening: {error_str}")

        with tab2:
            st.subheader("Sesuaikan Saldo (Modal Awal / Penarikan)")
            with st.form("adjust_balance_form"):
                target_account_label = st.selectbox("Pilih Akun", options=account_map.keys(), key="adj_acc")
                adj_type = st.radio("Jenis Penyesuaian", ["Pemasukan (Debit)", "Pengeluaran (Kredit)"])
                amount = st.number_input("Jumlah (Rp)", min_value=0, step=1000, format="%d")
                description = st.text_input("Deskripsi (e.g., Modal Awal, Penarikan Owner)")
                adj_date = st.date_input("Tanggal", value=datetime.date.today())
                submitted = st.form_submit_button("Proses Penyesuaian")
                if submitted:
                    final_amount = amount if adj_type == "Pemasukan (Kredit)" else -amount
                    target_account_id = account_map[target_account_label]['account_id']
                    supabase.rpc("adjust_account_balance", {
                        "p_account_id": target_account_id,
                        "p_amount": final_amount,
                        "p_description": description,
                        "p_user": admin_user,
                        "p_transaction_date": adj_date.isoformat()
                    }).execute()
                    st.success("Saldo berhasil disesuaikan!")
                    st.rerun()

        with tab3:
            st.subheader("Transfer Dana Antar Rekening")
            if len(accounts) < 2:
                st.info("Perlu minimal 2 rekening untuk melakukan transfer.")
            else:
                with st.form("transfer_funds_form"):
                    from_account_label = st.selectbox("Dari Akun", options=account_map.keys(), key="from_acc")
                    to_account_label = st.selectbox("Ke Akun", options=account_map.keys(), key="to_acc")
                    transfer_amount = st.number_input("Jumlah Transfer (Rp)", min_value=0, step=1000, format="%d")
                    transfer_desc = st.text_input("Catatan", value="Transfer internal")
                    transfer_date = st.date_input("Tanggal Transfer", value=datetime.date.today())
                    submitted = st.form_submit_button("Proses Transfer")
                    if submitted:
                        from_account = account_map[from_account_label]
                        to_account = account_map[to_account_label]
                        if from_account['account_id'] == to_account['account_id']:
                            st.error("Rekening asal dan tujuan tidak boleh sama.")
                        elif transfer_amount > from_account['balance']:
                            st.error("Saldo di rekening asal tidak mencukupi.")
                        else:
                            supabase.rpc("transfer_funds", {
                                "p_from_account_id": from_account['account_id'],
                                "p_to_account_id": to_account['account_id'],
                                "p_amount": transfer_amount,
                                "p_description": transfer_desc,
                                "p_user": admin_user,
                                "p_transaction_date": transfer_date.isoformat()
                            }).execute()
                            st.success("Transfer dana berhasil!")
                            st.rerun()
