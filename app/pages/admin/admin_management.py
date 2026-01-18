import streamlit as st
from app.db import get_client
from app.auth import change_password, reset_password_admin
import pandas as pd
import datetime

def show():
    st.title("Manajemen Toko")
    
    supabase = get_client()
    admin_user = st.session_state.get("username")
    
    tab1, tab2 = st.tabs(["Manajemen Toko", "Keamanan"])
    
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
                store_name = st.text_input("Nama Toko (Username)*", placeholder="Contoh: SuryaJaya")
                store_display_name = st.text_input("Nama Tampilan Toko*", placeholder="Contoh: TokoKeramik_SuryaJaya")
                password = st.text_input("Password (min 6 karakter)*", type="password")
                confirm_password = st.text_input("Konfirmasi Password*", type="password")
                
                st.divider()
                confirm_add = st.checkbox("Data toko sudah benar")
                submitted = st.form_submit_button("➕ Daftarkan Toko", use_container_width=True, type="primary")
                
                if submitted:
                    if not confirm_add:
                        st.error("Harap centang konfirmasi terlebih dahulu!")
                        st.stop()
                    if not store_name.strip() or not store_display_name.strip():
                        st.error("Nama toko dan nama tampilan harus diisi!")
                        st.stop()
                    
                    if len(password) < 6:
                        st.error("Password minimal 6 karakter!")
                        st.stop()
                    
                    if password != confirm_password:
                        st.error("Password tidak cocok!")
                        st.stop()
                    
                    try:
                        from werkzeug.security import generate_password_hash
                        
                        check_user = supabase.table("users").select("*").eq("username", store_name).execute()
                        if check_user.data:
                            st.error(f"Username '{store_name}' sudah ada!")
                            st.stop()
                        
                        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
                        
                        new_user = {
                            "username": store_name,
                            "password": hashed_password,
                            "role": "pegawai",
                            "store": store_display_name
                        }
                        
                        response = supabase.table("users").insert(new_user).execute()
                        if response.data:
                            st.success(f"✅ Toko '{store_display_name}' berhasil dibuat dengan username '{store_name}'!")
                            st.rerun()
                        else:
                            st.error("Gagal membuat toko. Silakan coba lagi.")
                    
                    except Exception as e:
                        error_str = str(e)
                        if "duplicate key" in error_str.lower() or "unique constraint" in error_str.lower():
                            st.error(f"Username '{store_name}' sudah terdaftar di sistem. Gunakan username lain.")
                        elif "user_id" in error_str:
                            st.error("Error: Gagal generate ID pengguna.")
                        else:
                            st.error(f"Gagal membuat toko: {error_str}")
        
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
                        
                        st.divider()
                        confirm_edit = st.checkbox("Ubah nama toko")
                        submitted = st.form_submit_button("💾 Update Nama Toko", use_container_width=True)
                        
                        if submitted:
                            if not confirm_edit:
                                st.error("Harap centang konfirmasi terlebih dahulu!")
                                st.stop()
                            if new_store_name != selected_store:
                                try:
                                    response = supabase.table("users").update({"store": new_store_name}).eq("store", selected_store).execute()
                                    if response.data:
                                        st.success(f"✅ Nama toko berhasil diubah dari '{selected_store}' ke '{new_store_name}'!")
                                        st.rerun()
                                    else:
                                        st.error("Gagal mengupdate nama toko. Silakan coba lagi.")
                                except Exception as e:
                                    error_str = str(e)
                                    if "duplicate key" in error_str.lower() or "unique constraint" in error_str.lower():
                                        st.error(f"Nama toko '{new_store_name}' sudah ada. Gunakan nama lain.")
                                    else:
                                        st.error(f"Error: {error_str}")
                            else:
                                st.info("Tidak ada perubahan data.")
                else:
                    st.info("Belum ada toko untuk diedit.")
            except Exception as e:
                st.error(f"Error: {e}")
    
    # Security Management
    with tab2:
        st.header("Manajemen Keamanan")
        
        sec_tab1, sec_tab2 = st.tabs(["Ubah Password Admin", "Reset Password Toko"])
        
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
            st.subheader("Reset Password Toko Lain")
            st.warning("⚠️ Tindakan ini akan mengubah password Toko secara permanen.")
            try:
                users = supabase.table("users").select("username, role").execute()
                if users.data:
                    usernames = [u['username'] for u in users.data if u['role'] != 'admin' or u['username'] != admin_user]
                    
                    if usernames:
                        selected_user = st.selectbox("Pilih User", options=usernames)
                        
                        with st.form("reset_pass_form"):
                            new_pass = st.text_input("Password Baru", type="password")
                            confirm = st.text_input("Konfirmasi Password", type="password")
                            
                            st.divider()
                            confirm_reset = st.checkbox(f"Reset password untuk **{selected_user}**")
                            submitted = st.form_submit_button("Reset Password", use_container_width=True, type="primary", disabled=not confirm_reset)
                            
                            if submitted and confirm_reset:
                                if len(new_pass) < 6:
                                    st.error("Password minimal 6 karakter!")
                                elif new_pass != confirm:
                                    st.error("Password tidak cocok!")
                                else:
                                    if reset_password_admin(selected_user, new_pass):
                                        st.success(f"✅ Password '{selected_user}' berhasil direset!")
                                        st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")
