from .base_repository import BaseRepository
from typing import List, Dict


class AuctionRepository(BaseRepository):
    def fetch_by_date_range(self, start: str, end: str) -> List[Dict]:
        return (
            self.supabase.table("auctions")
            .select("*")
            .gte("created_at", start)
            .lte("created_at", end)
            .execute()
        ).data

    def insert_many(self, data: List[Dict]):
        return self.supabase.table("auctions").insert(data).execute()

    def update_by_id(self, data: Dict, id: str):
        return self.supabase.table("auctions").update(data).eq("id", id).execute()
