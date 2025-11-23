# repositories/crawl_log_repository.py


class CrawlLogRepository:
    def __init__(self, supabase):
        self.supabase = supabase

    def insert_log(self, log_data: dict):
        """크롤 시작 시 기록 생성 (supabase-py v2 맞춤)"""
        res = self.supabase.table("crawl_logs").insert(log_data).execute()

        if not res.data:
            raise Exception("crawl_logs insert failed")

        return res.data  # → [{"id": 123, ...}]

    def finish_log(self, log_id: int, new_count: int, updated_count: int):
        """크롤 종료 시 업데이트"""
        res = (
            self.supabase.table("crawl_logs")
            .update(
                {
                    "ended_at": "now()",
                    "new_count": new_count,
                    "updated_count": updated_count,
                }
            )
            .eq("id", log_id)
            .execute()
        )

        return res.data
