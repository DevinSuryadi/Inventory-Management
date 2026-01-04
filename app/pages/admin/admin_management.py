import streamlit as st
from app.db import get_client
from app.auth import change_password, reset_password_admin
import pandas as pd
import datetime

def show():
    st.title("Manajemen Toko & User")
    
    supabase = get_client()
    admin_user = st.session_state.get("username")
    
    tab1, tab2, tab3, tab4 = st.tabs(["Manajemen Toko", "Manajemen User", "Keamanan", "Laporan"])
    
    # Manajemen Toko
    with tab1:
        st.header("Kelola Data Toko")
        
        # Sub-tabs untuk toko
        toko_tab1, toko_tab2, toko_tab3 = st.tabs(["Lihat Toko", "Tambah Toko", "Edit Toko"])
        
        # View Toko
        with toko_tab1:
            st.subheader("Daftar Toko")
            try:
                users_resp = supabase.table("users").select("store").neq("role", "admin").execute()
                stores = sorted(list(set([user['store'] for user in users_resp.data if user['store']])))
                
                if stores:
                    # Count staff per toko
                    store_data = []
                    for store in stores:
                        count_resp = supabase.table("users").select("*", count='exact').eq("store", store).eq("role", "pegawai").execute()
                        staff_count = count_resp.count if count_resp.count else 0
                        store_data.append({
                            "Nama Toko": store,
                            "Jumlah Staff": staff_count,
                            "Status": "Aktif"
                        })
                    
                    df = pd.DataFrame(store_data)
                    st.dataframe(df, use_container_width=True, hide_index=True)
                else:
                    st.info("Belum ada toko yang terdaftar.")
            except Exception as e:
                st.error(f"Error: {e}")
        
        # Add Toko
        with toko_tab2:
            st.subheader("Daftarkan Toko Baru")
            with st.form("add_store_form"):
                store_name = st.text_input("Nama Toko*", placeholder="Contoh: Toko Keramik Kota")
                store_address = st.text_area("Alamat Toko", placeholder="Jalan, RT/RW, Kota...")
                store_phone = st.text_input("Nomor Telepon", placeholder="08xx-xxxx-xxxx")
                manager_name = st.text_input("Nama Manager/Pemilik", placeholder="Nama manajer toko")
                manager_username = st.text_input("Username Manager (akan dibuat akun pegawai)", placeholder="username_manager")
                
                col1, col2 = st.columns(2)
                with col1:
                    initial_password = st.text_input("Password Awal (min 6 char)", type="password")
                with col2:
                    confirm_password = st.text_input("Konfirmasi Password", type="password")
                
                submitted = st.form_submit_button("Buat Toko & Akun Manager", use_container_width=True, type="primary")
                
                if submitted:
                    # Validasi
                    if not store_name.strip():
                        st.error("Nama toko harus diisi!")
                        st.stop()
                    
                    if not manager_username.strip():
                        st.error("Username manager harus diisi!")
                        st.stop()
                    
                    if len(initial_password) < 6:
                        st.error("Password minimal 6 karakter!")
                        st.stop()
                    
                    if initial_password != confirm_password:
                        st.error("Password tidak cocok!")
                        st.stop()
                    
                    try:
                        from werkzeug.security import generate_password_hash
                        
                        # Cek duplikasi toko
                        check_store = supabase.table("users").select("*").eq("store", store_name).execute()
                        if check_store.data:
                            st.error(f"Toko '{store_name}' sudah ada!")
                            st.stop()
                        
                        # Cek duplikasi username
                        check_user = supabase.table("users").select("*").eq("username", manager_username).execute()
                        if check_user.data:
                            st.error(f"Username '{manager_username}' sudah ada!")
                            st.stop()
                        
                        # Hash password
                        hashed_password = generate_password_hash(initial_password, method='pbkdf2:sha256')
                        
                        # Buat user baru (manager/pegawai)
                        new_user = {
                            "username": manager_username,
                            "password": hashed_password,
                            "role": "pegawai",
                            "store": store_name,
                            "full_name": manager_name
                        }
                        supabase.table("users").insert(new_user).execute()
                        
                        st.success(f"Toko '{store_name}' berhasil dibuat dengan manager '{manager_username}'!")
                        st.rerun()
                    
                    except Exception as e:
                        st.error(f"Error: {e}")
        
        # Edit Toko
        with toko_tab3:
            st.subheader("Edit Data Toko")
            try:
                users_resp = supabase.table("users").select("store").neq("role", "admin").execute()
                stores = sorted(list(set([user['store'] for user in users_resp.data if user['store']])))
                
                if stores:
                    selected_store = st.selectbox("Pilih Toko yang Akan Diedit", options=stores)
                    
                    with st.form("edit_store_form"):
                        new_store_name = st.text_input("Nama Toko Baru", value=selected_store)
                        submitted = st.form_submit_button("Update Nama Toko", use_container_width=True)
                        
                        if submitted:
                            if new_store_name != selected_store:
                                # Update semua user dengan store lama ke store baru
                                supabase.table("users").update({"store": new_store_name}).eq("store", selected_store).execute()
                                st.success(f"Nama toko berhasil diubah dari '{selected_store}' ke '{new_store_name}'!")
                                st.rerun()
                            else:
                                st.info("Tidak ada perubahan data.")
                else:
                    st.info("Belum ada toko untuk diedit.")
            except Exception as e:
                st.error(f"Error: {e}")

    # Manajemen User
    with tab2:
        st.header("Kelola User & Staff")
        
        user_tab1, user_tab2, user_tab3 = st.tabs(["Lihat User", "Tambah User",  "Nonaktifkan User"])
        
        # View User
        with user_tab1:
            st.subheader("Daftar User Sistem")
            try:
                users = supabase.table("users").select("username, role, store, created_at").order("role", desc=True).execute()
                if users.data:
                    user_list = []
                    for user in users.data:
                        user_list.append({
                                "Username": user['username'],
                                "Role": user['role'].replace('admin', 'Admin').replace('pegawai', 'Pegawai'),
                                "Toko": user['store'] or "-",
                                "Status": "Aktif"
                            })
                    df = pd.DataFrame(user_list)
                    st.dataframe(df, use_container_width=True, hide_index=True)
                else:
                    st.info("Tidak ada user.")
            except Exception as e:
                st.error(f"Error: {e}")
        
        # Add User
        with user_tab2:
            st.subheader("Tambah User Baru")
            with st.form("add_user_form"):
                username = st.text_input("Username*", placeholder="username")
                full_name = st.text_input("Nama Lengkap", placeholder="Nama user")
                
                col1, col2 = st.columns(2)
                with col1:
                    role = st.selectbox("Role", ["pegawai", "admin"])
                with col2:
                    if role == "pegawai":
                        users_resp = supabase.table("users").select("store").neq("role", "admin").execute()
                        stores = sorted(list(set([u['store'] for u in users_resp.data if u['store']])))
                        selected_store = st.selectbox("Pilih Toko", options=stores if stores else [""])
                    else:
                        selected_store = None
                
                col3, col4 = st.columns(2)
                with col3:
                    password = st.text_input("Password (min 6 char)", type="password")
                with col4:
                    confirm_pass = st.text_input("Konfirmasi Password", type="password")
                
                submitted = st.form_submit_button("Buat User", use_container_width=True, type="primary")
                
                if submitted:
                    if not username.strip():
                        st.error("Username harus diisi!")
                        st.stop()
                    
                    if len(password) < 6:
                        st.error("Password minimal 6 karakter!")
                        st.stop()
                    
                    if password != confirm_pass:
                        st.error("Password tidak cocok!")
                        st.stop()
                    
                    if role == "pegawai" and not selected_store:
                        st.error("Pilih toko untuk staff!")
                        st.stop()
                    
                    try:
                        from werkzeug.security import generate_password_hash
                        
                        # Cek duplikasi
                        check = supabase.table("users").select("*").eq("username", username).execute()
                        if check.data:
                            st.error(f"Username '{username}' sudah ada!")
                            st.stop()
                        
                        hashed = generate_password_hash(password, method='pbkdf2:sha256')
                        
                        new_user = {
                            "username": username,
                            "password": hashed,
                            "role": role,
                            "store": selected_store if role == "pegawai" else None,
                            "full_name": full_name
                        }
                        supabase.table("users").insert(new_user).execute()
                        
                        st.success(f"User '{username}' berhasil dibuat!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")
        
        # User Deactivation
        with user_tab3:
            st.subheader("Nonaktifkan User")
            st.warning("Fitur ini akan menghapus akun user dari sistem.")
            
            try:
                users = supabase.table("users").select("username, role").execute()
                if users.data:
                    usernames = [u['username'] for u in users.data if u['role'] != 'admin']
                    
                    if usernames:
                        selected_user = st.selectbox("Pilih User untuk Dihapus", options=usernames)
                        
                        if st.button("Hapus User", use_container_width=True, type="primary"):
                            if st.checkbox(f"Saya yakin ingin menghapus '{selected_user}'"):
                                try:
                                    supabase.table("users").delete().eq("username", selected_user).execute()
                                    st.success(f"User '{selected_user}' berhasil dihapus!")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error: {e}")
                    else:
                        st.info("Tidak ada staff yang bisa dihapus.")
            except Exception as e:
                st.error(f"Error: {e}")
    
    # Security Management
    with tab3:
        st.header("Manajemen Keamanan")
        
        sec_tab1, sec_tab2 = st.tabs(["Ubah Password Saya", "Reset Password User"])
        
        # Admin Password Change
        with sec_tab1:
            st.subheader("Ubah Password Akun Admin")
            with st.form("change_pass_form"):
                old_password = st.text_input("Password Lama", type="password")
                new_password = st.text_input("Password Baru (min 6 char)", type="password")
                confirm_new = st.text_input("Konfirmasi Password Baru", type="password")
                
                submitted = st.form_submit_button("Ubah Password", use_container_width=True, type="primary")
                
                if submitted:
                    if len(new_password) < 6:
                        st.error("Password minimal 6 karakter!")
                    elif new_password != confirm_new:
                        st.error("Password baru tidak cocok!")
                    else:
                        if change_password(admin_user, old_password, new_password):
                            st.success("Password berhasil diubah!")

        # User Password Reset
        with sec_tab2:
            st.subheader("Reset Password User Lain")
            try:
                users = supabase.table("users").select("username, role").execute()
                if users.data:
                    usernames = [u['username'] for u in users.data if u['role'] != 'admin' or u['username'] != admin_user]
                    
                    if usernames:
                        selected_user = st.selectbox("Pilih User", options=usernames)
                        
                        with st.form("reset_pass_form"):
                            new_pass = st.text_input("Password Baru", type="password")
                            confirm = st.text_input("Konfirmasi Password", type="password")
                            
                            submitted = st.form_submit_button("Reset Password", use_container_width=True, type="primary")
                            
                            if submitted:
                                if len(new_pass) < 6:
                                    st.error("Password minimal 6 karakter!")
                                elif new_pass != confirm:
                                    st.error("Password tidak cocok!")
                                else:
                                    if reset_password_admin(selected_user, new_pass):
                                        st.success(f"Password '{selected_user}' berhasil direset!")
                                        st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")
    
    # Reports
    with tab4:
        st.header("Laporan Sistem")
        
        col1, col2, col3 = st.columns(3)
        
        try:
            # Total Toko
            users_resp = supabase.table("users").select("store").neq("role", "admin").execute()
            total_stores = len(set([u['store'] for u in users_resp.data if u['store']]))
            col1.metric("Total Toko", total_stores)
            
            # Total User
            all_users = supabase.table("users").select("*", count='exact').execute()
            col2.metric("Total User", all_users.count)
            
            # Total Admin
            admins = supabase.table("users").select("*", count='exact').eq("role", "admin").execute()
            col3.metric("Total Admin", admins.count)
            
            st.divider()
            
            # Aktivitas Login
            st.subheader("Statistik Sistem")
            st.info("Fitur logging tersedia untuk melacak aktivitas user. Cek logs/ folder untuk detail.")
            
        except Exception as e:
            st.error(f"Error: {e}")
