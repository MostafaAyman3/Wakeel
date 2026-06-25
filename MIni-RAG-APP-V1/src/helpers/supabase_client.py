from supabase import create_client, Client
from helpers.config import get_settings

def get_supabase_client() -> Client:
    settings = get_settings()
    url: str = settings.SUPABASE_URL
    key: str = settings.SUPABASE_SERVICE_ROLE_KEY # Use service role key for backend operations
    return create_client(url, key)
