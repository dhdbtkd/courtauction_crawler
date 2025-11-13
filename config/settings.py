import os
from dotenv import load_dotenv
from utils.env_utils import is_oracle_instance


def load_settings():
    """
    .env 파일을 절대경로 기준으로 안전하게 로드
    """
    if is_oracle_instance():
        env_path = "/home/ubuntu/scripts/.env"
    else:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        root_dir = os.path.abspath(os.path.join(current_dir, ".."))
        env_path = os.path.join(root_dir, ".env")
        if not os.path.exists(env_path):
            env_path = os.path.join(os.getcwd(), ".env")

    print(f"[settings] Loading .env from: {env_path}")

    if os.path.exists(env_path):
        load_dotenv(dotenv_path=env_path, override=True)
    else:
        print(f"⚠️  .env 파일을 찾을 수 없습니다. ({env_path})")


def get_env(name: str, default=None):
    """환경변수 헬퍼"""
    val = os.getenv(name, default)
    if val is None:
        print(f"⚠️  환경변수 {name} 누락 (기본값 사용: {default})")
    return val


# ✅ 이제 load_settings() 이후 호출해야 함
SUPABASE_URL = None
SUPABASE_KEY = None
SLACK_TOKEN = None
TELEGRAM_BOT_API_KEY = None
TELEGRAM_CHAT_ID = None


def init_settings():
    """환경변수를 실제로 settings에 반영"""
    global \
        SUPABASE_URL, \
        SUPABASE_KEY, \
        SLACK_TOKEN, \
        TELEGRAM_BOT_API_KEY, \
        TELEGRAM_CHAT_ID
    SUPABASE_URL = get_env("SUPABASE_URL")
    SUPABASE_KEY = get_env("SUPABASE_KEY")
    SLACK_TOKEN = get_env("SLACK_TOKEN")
    TELEGRAM_BOT_API_KEY = get_env("TELEGRAM_BOT_API_KEY")
    TELEGRAM_CHAT_ID = get_env("TELEGRAM_CHAT_ID")
