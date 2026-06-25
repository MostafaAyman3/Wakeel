from helpers.config import get_settings, Settings
from helpers.supabase_client import get_supabase_client

class BaseDataModel:
    def __init__(self):
        self.settings: Settings = get_settings()
        self.supabase = get_supabase_client()

