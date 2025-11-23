# core/supabase.py
from supabase import create_client
from config.settings import settings

# 전역 Supabase Client (FastAPI 전역에서 사용 가능)
supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
