# app/db.py
from app.supabase_client import supabase

def get_client():
    return supabase