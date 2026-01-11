import streamlit as st
from app.db import get_client
from werkzeug.security import check_password_hash, generate_password_hash
import logging

# Setup logging
logger = logging.getLogger(__name__)

def hash_password(password: str) -> str:
    return generate_password_hash(password, method='pbkdf2:sha256')

def verify_password(password: str, hashed: str) -> bool:

    try:
        return check_password_hash(hashed, password)
    except Exception as e:
        logger.error(f"Password verification error: {e}")
        return False

def login(username: str, password: str) -> bool:
    
    # Validasi input
    if not username or not password:
        st.error("Username dan password harus diisi.")
        return False
    
    # Additional validationx``
    if len(username) < 3:
        st.error("Username minimal 3 karakter.")
        return False
    
    if len(password) < 1:
        st.error("Password minimal 2 karakter.")
        return False

    try:
        supabase = get_client()
        response = supabase.table("users").select("*").eq("username", username).single().execute()

        user_data = response.data
        
        # Verify password hash
        if user_data and verify_password(password, user_data['password']):
            st.session_state.logged_in = True
            st.session_state.username = user_data['username']
            st.session_state.role = user_data['role']
            st.session_state.store = user_data['store']
            
            # Log successful login
            logger.info(f"User {username} (role: {user_data['role']}) successfully logged in")
            
            return True
        else:
            st.error("Username atau password salah.")
            logger.warning(f"Failed login attempt for username: {username}")
            return False
    
    except Exception as e:
        st.error("Username atau password salah.")
        logger.error(f"Login error: {e}")
        return False

def logout():
    keys_to_delete = ['logged_in', 'username', 'role', 'store']
    for key in keys_to_delete:
        if key in st.session_state:
            del st.session_state[key]
    
    logger.info("User logged out")

def change_password(username: str, old_password: str, new_password: str) -> bool:
    
    # Validasi
    if len(new_password) < 6:
        st.error("Password baru minimal 6 karakter.")
        return False
    
    if old_password == new_password:
        st.error("Password baru tidak boleh sama dengan password lama.")
        return False
    
    try:
        supabase = get_client()
        response = supabase.table("users").select("password").eq("username", username).single().execute()
        user_data = response.data
        
        # Verify old password
        if not verify_password(old_password, user_data['password']):
            st.error("Password lama tidak sesuai.")
            return False
        
        # Hash new password
        hashed_new = hash_password(new_password)
        
        # Update password
        response = supabase.table("users").update({"password": hashed_new}).eq("username", username).execute()
        
        if response.data:
            logger.info(f"Password changed for user: {username}")
            st.success("Password berhasil diubah!")
            return True
        else:
            st.error("Gagal mengubah password. Silakan coba lagi.")
            return False
        
    except Exception as e:
        error_str = str(e)
        if "not found" in error_str.lower() or "no rows" in error_str.lower():
            st.error("User tidak ditemukan.")
        else:
            st.error(f"Terjadi kesalahan: {error_str}")
        return False
        logger.error(f"Change password error: {e}")
        return False

def reset_password_admin(username: str, new_password: str) -> bool:
    
    if len(new_password) < 2:
        st.error("Password minimal 2 karakter.")
        return False
    
    try:
        supabase = get_client()
        hashed_password = hash_password(new_password)
        response = supabase.table("users").update({"password": hashed_password}).eq("username", username).execute()
        
        if response.data:
            logger.info(f"Admin reset password for user: {username}")
            st.success(f"Password user '{username}' berhasil direset!")
            return True
        else:
            st.error(f"User '{username}' tidak ditemukan.")
            return False
        
    except Exception as e:
        error_str = str(e)
        if "not found" in error_str.lower() or "no rows" in error_str.lower():
            st.error(f"User '{username}' tidak ditemukan.")
        else:
            st.error(f"Gagal mereset password: {error_str}")
        logger.error(f"Admin reset password error: {e}")
        return False
        return False
