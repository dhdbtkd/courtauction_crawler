from .base_repository import BaseRepository
from typing import List, Dict


class NotificationRepository(BaseRepository):
    def get_active_rules(self) -> List[Dict]:
        """활성화된 모든 알림 규칙 조회"""
        return (
            self.supabase.table("notification_rules")
            .select("*")
            .eq("enabled", True)
            .execute()
        ).data

    def get_channels_by_user(self, user_id: str) -> List[Dict]:
        """유저별 알림 채널(slack, telegram 등)"""
        return (
            self.supabase.table("notification_channels")
            .select("*")
            .eq("user_id", user_id)
            .eq("enabled", True)
            .execute()
        ).data

    def insert_notification_log(self, log_data: Dict):
        """발송 기록 저장"""
        return self.supabase.table("notifications_log").insert(log_data).execute()
