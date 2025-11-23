from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
import os


class Settings(BaseSettings):
    # ====== 환경변수 목록 ======
    SUPABASE_URL: str
    SUPABASE_KEY: str

    SLACK_TOKEN: str | None = None
    TELEGRAM_BOT_API_KEY: str | None = None
    TELEGRAM_CHAT_ID: str | None = None

    NAVER_ACCESS_KEY: str | None = None
    NAVER_CLIENT_SECRET: str | None = None

    ADMIN_SECRET: str
    DEBUG: bool = False

    # ====== pydantic v2 설정 ======
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # .env에 더 많은 항목이 있어도 무시
    )


@lru_cache
def get_settings():
    """
    서버 환경에 따라 다른 경로에서 .env 로드
    """
    # ORACLE 같은 특정 서버라면 별도 경로
    if os.getenv("ORACLE_INSTANCE") == "1":
        return Settings(_env_file="/home/ubuntu/scripts/.env")

    # 기본 .env
    return Settings()


# 최종적으로 settings 객체 생성
settings = get_settings()
