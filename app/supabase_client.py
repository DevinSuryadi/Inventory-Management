# app/supabase_client.py
import os
from supabase import create_client
from dotenv import load_dotenv  # type: ignore

# Load variabel environment dari .env
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("SUPABASE_URL atau SUPABASE_KEY tidak ditemukan di .env")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
