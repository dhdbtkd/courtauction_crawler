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

    def insert_many(
        self, data: List[Dict]
    ) -> List[str]:  # 반환 타입을 List[str]로 명시 (ID가 문자열이라 가정)
        # Supabase 삽입 실행
        response = self.supabase.table("auctions").insert(data).execute()

        # 🌟 개선: 응답 데이터에서 삽입된 레코드의 ID만 추출
        if response and response.data:
            # 삽입된 데이터 리스트에서 각 항목의 'id' 값을 추출하여 반환
            inserted_ids = [item.get("id") for item in response.data]
            return inserted_ids

        return []

    def update_by_id(self, data: Dict, id: str):
        return self.supabase.table("auctions").update(data).eq("id", id).execute()
