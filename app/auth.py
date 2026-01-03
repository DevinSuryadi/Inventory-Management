# app/auth.py

import streamlit as st
from app.db import get_client

def login(username, password):
    """
    Memverifikasi kredensial pengguna dan mengatur session state jika berhasil.
    Mengembalikan True jika login berhasil, False jika gagal.
    """
    if not username or not password:
        st.error("Username dan password harus diisi.")
        return False

    try:
        supabase = get_client()
        # Cari user berdasarkan username
        response = supabase.table("users").select("*").eq("username", username).single().execute()

        user_data = response.data
        
        # PERINGATAN KEAMANAN:
        # Di aplikasi produksi, JANGAN PERNAH membandingkan password secara langsung.
        # Gunakan library hashing seperti 'bcrypt' atau 'argon2'.
        # Contoh: if bcrypt.checkpw(password.encode(), user_data['password'].encode()):
        if user_data and user_data['password'] == password:
            # Simpan informasi user ke session state
            st.session_state.logged_in = True
            st.session_state.username = user_data['username']
            st.session_state.role = user_data['role']
            st.session_state.store = user_data['store']
            return True
        else:
            st.error("Username atau password salah.")
            return False
    
    except Exception:
        st.error("Username atau password salah.")
        return False

def logout():
    """Membersihkan semua session state untuk logout."""
    keys_to_delete = list(st.session_state.keys())
    for key in keys_to_delete:
        del st.session_state[key]
