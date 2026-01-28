# app/supabase_client.py
import os
from supabase import create_client

# Coba ambil dari Streamlit Secrets terlebih dahulu (untuk deployment)
# Jika tidak ada, gunakan environment variables atau .env (untuk development lokal)
try:
    import streamlit as st
    SUPABASE_URL = st.secrets.get("SUPABASE_URL")
    SUPABASE_KEY = st.secrets.get("SUPABASE_KEY")
except (ImportError, AttributeError, KeyError):
    SUPABASE_URL = None
    SUPABASE_KEY = None

# Fallback ke environment variables jika tidak ada di Streamlit Secrets
if not SUPABASE_URL or not SUPABASE_KEY:
    from dotenv import load_dotenv
    load_dotenv()
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("SUPABASE_URL atau SUPABASE_KEY tidak ditemukan. "
                     "Pastikan sudah diset di Streamlit Secrets atau file .env")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
