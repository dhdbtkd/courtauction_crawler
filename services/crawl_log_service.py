# services/crawl_log_service.py
from core.supabase import supabase
from repositories.crawl_log_repository import CrawlLogRepository


class CrawlLogService:
    def __init__(self, repo: CrawlLogRepository, supabase: supabase):
        self.repo = repo
        self.supabase = supabase

    def get_sido_name(self, sido_code: str):
        res = (
            self.supabase.table("sido_code")
            .select("sido_name")
            .eq("sido_code", sido_code)
            .maybe_single()
            .execute()
        )
        return res.data["sido_name"] if res.data else None

    def get_sigu_name(self, sigu_code: str):
        print(sigu_code)
        res = (
            self.supabase.table("sigu_code")
            .select("sigu_name")
            .eq("sigu_code", sigu_code)
            .maybe_single()
            .execute()
        )
        return res.data["sigu_name"] if res.data else None

    def start(self, sido_code: str, sigu_code: str) -> int:
        print(sido_code)
        print(sigu_code)
        """크롤 시작 시 로그 생성"""
        log_data = {
            "sido_code": sido_code,
            "sigu_code": sigu_code,
            "sido_name": self.get_sido_name(sido_code),
            "sigu_name": self.get_sigu_name(sido_code + sigu_code),
        }

        inserted = self.repo.insert_log(log_data)
        return inserted[0]["id"]

    def finish(self, log_id: int, new_count: int, updated_count: int):
        """크롤 끝날 때 카운트 업데이트"""
        self.repo.finish_log(log_id, new_count, updated_count)
