import streamlit as st
from app.db import get_client
import pandas as pd
import datetime

def show():
    st.markdown("<h1 style='color: #e67e22;'>Biaya Operasional</h1>", unsafe_allow_html=True)

    # Initialize form key for reset
    if "expense_form_key" not in st.session_state:
        st.session_state.expense_form_key = 0

    try:
        supabase = get_client()
        
        # Get list of stores for admin
        users_resp = supabase.table("users").select("store").eq("role", "pegawai").execute()
        stores = sorted(list(set([user['store'] for user in users_resp.data if user['store']])))
        
        if not stores:
            st.warning("Belum ada toko yang terdaftar.")
            return

        # Store selector
        selected_store = st.selectbox("Pilih Toko", options=stores, key="expense_store_select")
        
        st.divider()

        tab1, tab2, tab3 = st.tabs(["Tambah Biaya", "Riwayat Biaya", "Bayar Gaji"])

        # Add Expense
        with tab1:
            st.subheader(f"Catat Biaya Operasional - {selected_store}")
            
            # Show success message if exists
            if st.session_state.get("expense_success"):
                st.success(st.session_state.expense_success)
                del st.session_state.expense_success
            
            with st.form(f"add_expense_form_{st.session_state.expense_form_key}", border=True):
                col_type, col_amount = st.columns(2)
                
                with col_type:
                    expense_type = st.text_input(
                        "Jenis Biaya*",
                        placeholder="Contoh: Bensin, Listrik, Sewa, dll...",
                        help="Ketik jenis biaya sesuai kebutuhan (bebas)"
                    )
                
                with col_amount:
                    amount = st.number_input("Jumlah (Rp)*", min_value=0, step=1000, format="%d")
                
                col_date, col_time = st.columns(2)
                with col_date:
                    expense_date = st.date_input("Tanggal", value=datetime.date.today())
                with col_time:
                    expense_time = st.time_input("Waktu", value=datetime.datetime.now().time())
                
                description = st.text_area(
                    "Keterangan",
                    placeholder="Deskripsi tambahan (opsional)..."
                )
                
                # Account selection
                accounts_resp = supabase.table("accounts").select("account_id, account_name, balance").eq("store", selected_store).execute()
                account_map = {f"{acc['account_name']} (Saldo: Rp {acc['balance']:,.0f})": acc['account_id'] for acc in accounts_resp.data or []}
                
                selected_account = None
                if account_map:
                    selected_account_label = st.selectbox("Bayar dari Rekening", options=account_map.keys())
                    selected_account = account_map[selected_account_label]
                else:
                    st.warning("Tidak ada rekening tersedia untuk toko ini.")
                
                st.divider()
                
                confirm = st.checkbox("Biaya ini sudah benar")
                submitted = st.form_submit_button("Simpan Biaya", use_container_width=True, type="primary")
                
                if submitted:
                    if not confirm:
                        st.error("Harap centang konfirmasi terlebih dahulu!")
                        st.stop()
                    
                    if not expense_type.strip():
                        st.error("Jenis biaya harus diisi!")
                        st.stop()
                    
                    if amount <= 0:
                        st.error("Jumlah biaya harus lebih dari 0!")
                        st.stop()
                        
                    expense_datetime = datetime.datetime.combine(expense_date, expense_time)
                    
                    try:
                        result = supabase.rpc("record_operational_expense", {
                            "p_store": selected_store,
                            "p_expense_type": expense_type.strip().lower(),
                            "p_amount": amount,
                            "p_description": description,
                            "p_reference_id": None,
                            "p_account_id": selected_account,
                            "p_expense_date": expense_datetime.isoformat(),
                            "p_created_by": st.session_state.get("username", "admin")
                        }).execute()
                        
                        st.session_state.expense_success = f"✅ Biaya '{expense_type}' sebesar Rp {amount:,.0f} berhasil dicatat!"
                        st.session_state.expense_form_key += 1
                        st.rerun()
                    except Exception as e:
                        st.error(f"Gagal menyimpan biaya: {e}")

        # Expense History
        with tab2:
            st.subheader(f"Riwayat Biaya - {selected_store}")
            
            col1, col2 = st.columns(2)
            with col1:
                start_date = st.date_input("Dari Tanggal", value=datetime.date.today().replace(day=1), key="exp_start")
            with col2:
                end_date = st.date_input("Sampai Tanggal", value=datetime.date.today(), key="exp_end")
            
            if st.button("Tampilkan Riwayat", key="btn_exp_hist", type="primary"):
                try:
                    response = supabase.table("operational_expense").select(
                        "expense_id, expense_type, amount, description, expense_date, created_by"
                    ).eq("store", selected_store).gte(
                        "expense_date", start_date.isoformat()
                    ).lt(
                        "expense_date", (end_date + datetime.timedelta(days=1)).isoformat()
                    ).order("expense_date", desc=True).execute()
                    
                    results = response.data
                    
                    if not results:
                        st.info("Tidak ada riwayat biaya untuk periode yang dipilih.")
                    else:
                        df = pd.DataFrame(results)
                        df = df.rename(columns={
                            'expense_id': 'ID',
                            'expense_type': 'Jenis',
                            'amount': 'Jumlah',
                            'description': 'Keterangan',
                            'expense_date': 'Tanggal',
                            'created_by': 'Oleh'
                        })
                        df['Jenis'] = df['Jenis'].str.capitalize()
                        df['Jumlah'] = df['Jumlah'].apply(lambda x: f"Rp {x:,.0f}")
                        df['Tanggal'] = pd.to_datetime(df['Tanggal']).dt.strftime('%Y-%m-%d %H:%M')
                        
                        st.dataframe(df[['ID', 'Tanggal', 'Jenis', 'Jumlah', 'Keterangan']], 
                                   use_container_width=True, hide_index=True)
                        
                        # Summary by type
                        st.subheader("Ringkasan per Jenis Biaya")
                        summary_df = pd.DataFrame(results).groupby('expense_type').agg({
                            'amount': 'sum',
                            'expense_id': 'count'
                        }).reset_index()
                        summary_df.columns = ['Jenis', 'Total', 'Jumlah Transaksi']
                        summary_df['Jenis'] = summary_df['Jenis'].str.capitalize()
                        summary_df['Total'] = summary_df['Total'].apply(lambda x: f"Rp {x:,.0f}")
                        st.dataframe(summary_df, use_container_width=True, hide_index=True)
                        
                        # Total
                        total = sum([r['amount'] for r in results])
                        st.metric("Total Biaya Periode Ini", f"Rp {total:,.0f}")
                        
                except Exception as e:
                    st.error(f"Gagal memuat riwayat: {e}")

        # Pay Salary
        with tab3:
            st.subheader(f"Bayar Gaji Karyawan - {selected_store}")
            
            # Get staff list
            staff_resp = supabase.table("pegawai").select(
                "pegawai_id, nama, gaji_bulanan, tanggal_pembayaran"
            ).eq("store", selected_store).order("nama").execute()
            
            staff_list = staff_resp.data or []
            
            if not staff_list:
                st.info(f"Belum ada pegawai terdaftar untuk toko {selected_store}.")
            else:
                staff_map = {
                    f"{s['nama']} (Gaji: Rp {s['gaji_bulanan']:,.0f})": s for s in staff_list
                }
                
                with st.form("pay_salary_form", border=True):
                    selected_staff_label = st.selectbox("Pilih Pegawai", options=staff_map.keys())
                    selected_staff = staff_map[selected_staff_label]
                    
                    col_month, col_amount = st.columns(2)
                    with col_month:
                        salary_month = st.date_input(
                            "Periode Gaji (Bulan)",
                            value=datetime.date.today().replace(day=1)
                        )
                    with col_amount:
                        salary_amount = st.number_input(
                            "Jumlah Gaji (Rp)", 
                            min_value=0, 
                            value=int(selected_staff['gaji_bulanan']),
                            step=10000
                        )
                    
                    col_date, col_time = st.columns(2)
                    with col_date:
                        pay_date = st.date_input("Tanggal Pembayaran", value=datetime.date.today())
                    with col_time:
                        pay_time = st.time_input("Waktu", value=datetime.datetime.now().time())
                    
                    note = st.text_input("Catatan", placeholder="Contoh: Gaji Januari 2026")
                    
                    # Account selection
                    accounts_resp = supabase.table("accounts").select("account_id, account_name, balance").eq("store", selected_store).execute()
                    account_map = {f"{acc['account_name']} (Saldo: Rp {acc['balance']:,.0f})": acc['account_id'] for acc in accounts_resp.data or []}
                    
                    selected_account = None
                    if account_map:
                        selected_account_label = st.selectbox("Bayar dari Rekening", options=account_map.keys(), key="salary_account")
                        selected_account = account_map[selected_account_label]
                    
                    st.divider()
                    
                    confirm = st.checkbox("Bayar gaji")
                    submitted = st.form_submit_button("Bayar Gaji", use_container_width=True, type="primary")
                    
                    if submitted:
                        if not confirm:
                            st.error("Harap centang konfirmasi terlebih dahulu!")
                            st.stop()
                            
                        pay_datetime = datetime.datetime.combine(pay_date, pay_time)
                        
                        try:
                            # Record as operational expense with type 'salary'
                            result = supabase.rpc("record_operational_expense", {
                                "p_store": selected_store,
                                "p_expense_type": "salary",
                                "p_amount": salary_amount,
                                "p_description": f"Gaji {selected_staff['nama']} - {salary_month.strftime('%B %Y')} - {note}",
                                "p_reference_id": selected_staff['pegawai_id'],
                                "p_account_id": selected_account,
                                "p_expense_date": pay_datetime.isoformat(),
                                "p_created_by": st.session_state.get("username", "admin")
                            }).execute()
                            
                            # Also update pegawai_payment table
                            try:
                                supabase.table("pegawai_payment").insert({
                                    "pegawai_id": selected_staff['pegawai_id'],
                                    "bulan": salary_month.isoformat(),
                                    "jumlah": salary_amount,
                                    "paid_at": pay_datetime.isoformat(),
                                    "status": "paid"
                                }).execute()
                            except:
                                pass
                            
                            st.success(f"✅ Gaji {selected_staff['nama']} berhasil dibayarkan!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Gagal membayar gaji: {e}")

    except Exception as e:
        st.error(f"Terjadi kesalahan: {e}")
