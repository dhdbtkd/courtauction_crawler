from supabase import create_client, Client


class BaseRepository:
    def __init__(self, url: str, key: str):
        self.supabase: Client = create_client(url, key)
