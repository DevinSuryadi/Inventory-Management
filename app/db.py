# app/db.py
from app.supabase_client import supabase

def get_client():
    """Mengembalikan instance Supabase client yang sudah diinisialisasi."""
    return supabase