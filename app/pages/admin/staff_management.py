import streamlit as st
from app.db import get_client
import pandas as pd
import datetime

def show():
    st.title("Manajemen Pegawai (Staff)")
    
    supabase = get_client()
    store = st.session_state.get("store")
    
    tab1, tab2, tab3 = st.tabs(["Lihat Pegawai", "Tambah Pegawai", "Hapus Pegawai"])
    
    # View Staff
    with tab1:
        st.subheader("Daftar Pegawai per Toko")
        try:
            # Get list of stores
            users_resp = supabase.table("users").select("store").neq("role", "admin").eq("role", "pegawai").execute()
            stores = sorted(list(set([user['store'] for user in users_resp.data if user['store']])))
            
            if stores:
                selected_store = st.selectbox("Pilih Toko", options=stores, key="view_staff_store")
                
                # Get staff for selected store
                staff_resp = supabase.table("pegawai").select("*").eq("store", selected_store).order("created_at", desc=True).execute()
                
                if staff_resp.data:
                    staff_list = []
                    for staff in staff_resp.data:
                        staff_list.append({
                            "ID": staff['pegawai_id'],
                            "Nama": staff['nama'],
                            "No Telp": staff.get('posisi', '-'),  # Using posisi field for phone number
                            "Gaji/Bulan": f"Rp {staff['gaji_bulanan']:,.0f}",
                            "Tgl Pembayaran": f"Tanggal {staff['tanggal_pembayaran']}",
                            "Dibuat": pd.to_datetime(staff['created_at']).strftime('%d/%m/%Y %H:%M')
                        })
                    
                    df = pd.DataFrame(staff_list)
                    st.dataframe(df, use_container_width=True, hide_index=True)
                    st.info(f"Total: {len(staff_list)} pegawai di toko {selected_store}")
                else:
                    st.info(f"Belum ada pegawai terdaftar untuk toko {selected_store}.")
            else:
                st.warning("Belum ada toko yang terdaftar.")
        except Exception as e:
            st.error(f"Error: {e}")
    
    # Add Staff
    with tab2:
        st.subheader("Daftarkan Pegawai Baru")
        try:
            # Get list of stores
            users_resp = supabase.table("users").select("store").neq("role", "admin").eq("role", "pegawai").execute()
            stores = sorted(list(set([user['store'] for user in users_resp.data if user['store']])))
            
            if stores:
                with st.form("add_staff_form"):
                    selected_store = st.selectbox("Pilih Toko*", options=stores, key="add_staff_store")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        staff_name = st.text_input("Nama Lengkap*", placeholder="Contoh: Ahmad Riyadi")
                    with col2:
                        staff_phone = st.text_input("No Telp*", placeholder="Contoh: 0812345678")
                    
                    col3, col4 = st.columns(2)
                    with col3:
                        staff_salary = st.number_input("Gaji Bulanan (Rp)*", min_value=0, step=10000, format="%d")
                    with col4:
                        payment_date = st.number_input("Tanggal Pembayaran (1-31)*", min_value=1, max_value=31, value=1)
                    
                    submitted = st.form_submit_button("Daftarkan Pegawai", use_container_width=True, type="primary")
                    
                    if submitted:
                        if not staff_name.strip() or not staff_phone.strip():
                            st.error("Nama dan no telp harus diisi!")
                            st.stop()
                        
                        if staff_salary <= 0:
                            st.error("Gaji harus lebih dari 0!")
                            st.stop()
                        
                        try:
                            new_staff = {
                                "store": selected_store,
                                "nama": staff_name,
                                "posisi": staff_phone, 
                                "gaji_bulanan": staff_salary,
                                "tanggal_pembayaran": int(payment_date),
                                "created_at": datetime.datetime.now().isoformat(),
                                "updated_at": datetime.datetime.now().isoformat()
                            }
                            response = supabase.table("pegawai").insert(new_staff).execute()
                            if response.data:
                                st.success(f"Pegawai '{staff_name}' berhasil ditambahkan!")
                                st.rerun()
                            else:
                                st.error("Gagal menambah pegawai. Silakan coba lagi.")
                        except Exception as e:
                            error_str = str(e)
                            if "duplicate key" in error_str.lower() or "unique constraint" in error_str.lower():
                                st.error(f"Data pegawai sudah ada. Gunakan nama atau data lain.")
                            elif "foreign key" in error_str.lower():
                                st.error("Error: Toko yang dipilih tidak valid. Silakan refresh halaman.")
                            else:
                                st.error(f"Gagal menambah pegawai: {error_str}")
            else:
                st.warning("Belum ada toko yang terdaftar untuk menambah pegawai.")
        except Exception as e:
            st.error(f"Error: {e}")
    
    # Delete Staff
    with tab3:
        st.subheader("Hapus Pegawai")
        st.warning("Tindakan ini akan menghapus data pegawai dari sistem.")
        
        try:
            # Get list of stores
            users_resp = supabase.table("users").select("store").neq("role", "admin").eq("role", "pegawai").execute()
            stores = sorted(list(set([user['store'] for user in users_resp.data if user['store']])))
            
            if stores:
                selected_store = st.selectbox("Pilih Toko", options=stores, key="delete_staff_store")
                
                # Get staff for selected store
                staff_resp = supabase.table("pegawai").select("pegawai_id, nama, gaji_bulanan").eq("store", selected_store).order("nama", desc=False).execute()
                
                if staff_resp.data:
                    staff_options = {f"{s['nama']} (Rp {s['gaji_bulanan']:,.0f})": s['pegawai_id'] for s in staff_resp.data}
                    
                    selected_staff_display = st.selectbox("Pilih Pegawai untuk Dihapus", options=list(staff_options.keys()))
                    selected_staff_id = staff_options[selected_staff_display]
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("Hapus Pegawai", use_container_width=True, type="primary"):
                            with col2:
                                confirm = st.checkbox(f"Saya yakin ingin menghapus: {selected_staff_display}")
                            
                            if confirm:
                                try:
                                    response = supabase.table("pegawai").delete().eq("pegawai_id", selected_staff_id).execute()
                                    st.success("Pegawai berhasil dihapus!")
                                    st.rerun()
                                except Exception as e:
                                    error_str = str(e)
                                    if "foreign key" in error_str.lower():
                                        st.error("Gagal menghapus: Pegawai ini terkait dengan data lain. Hubungi administrator.")
                                    else:
                                        st.error(f"Gagal menghapus pegawai: {error_str}")
                else:
                    st.info(f"Belum ada pegawai di toko {selected_store}.")
            else:
                st.warning("Belum ada toko yang terdaftar.")
        except Exception as e:
            st.error(f"Error: {e}")
