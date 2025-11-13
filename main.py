# main.py
import os
import asyncio
import requests
from datetime import datetime
from fastapi import FastAPI, Request
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from supabase import create_client

from services.crawler_service import CrawlerService
from services.notification_service import NotificationService
from repositories.auction_repository import AuctionRepository
from repositories.notification_repository import NotificationRepository
from services.notifier_service import NotifierService
from config import settings

settings.load_settings()
settings.init_settings()
# --------------------------------------------------
# ✅ FastAPI 앱 생성
# --------------------------------------------------
app = FastAPI(title="CourtAuction Bot", version="1.0.0")

# --------------------------------------------------
# ✅ Supabase 클라이언트
# --------------------------------------------------
supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)


# --------------------------------------------------
# ✅ Telegram Webhook 처리
# --------------------------------------------------
@app.post("/")
async def telegram_webhook(request: Request):
    """Telegram Webhook Handler"""
    data = await request.json()
    print("📩 Telegram webhook received:", data)

    message = data.get("message", {})
    chat = message.get("chat", {})
    text = message.get("text", "")
    chat_id = str(chat.get("id"))

    if not chat_id or not text:
        return {"ok": False}

    # ✅ /start 명령 처리
    if text.startswith("/start"):
        parts = text.split(" ")
        if len(parts) < 2:
            await send_message(
                chat_id, "❌ 인증 토큰이 없습니다. 웹사이트에서 다시 연결해주세요."
            )
            return {"ok": True}

        token = parts[1].strip()

        res = (
            supabase.table("users")
            .select("id, email")
            .eq("telegram_auth_token", token)
            .single()
            .execute()
        )

        if not res.data:
            await send_message(chat_id, "❌ 잘못된 토큰입니다. 다시 시도해주세요.")
            return {"ok": True}

        user_id = res.data["id"]
        email = res.data["email"]

        supabase.table("notification_channels").upsert(
            {
                "user_id": user_id,
                "type": "telegram",
                "identifier": chat_id,
                "enabled": True,
            }
        ).execute()

        supabase.table("users").update({"telegram_auth_token": None}).eq(
            "id", user_id
        ).execute()

        await send_message(
            chat_id, f"✅ 텔레그램 알림이 연결되었습니다!\n\n계정: {email}"
        )
        print(f"✅ Telegram linked: user={email}, chat_id={chat_id}")
        return {"ok": True}

    await send_message(
        chat_id, "🤖 명령어를 인식하지 못했습니다. /start 로 다시 시도해주세요."
    )
    return {"ok": True}


async def send_message(chat_id: str, text: str):
    """텔레그램으로 메시지 보내기"""
    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_API_KEY}/sendMessage"
    data = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    try:
        requests.post(url, data=data)
    except Exception as e:
        print("⚠️ Telegram send_message error:", e)


# --------------------------------------------------
# ✅ 주기적 크롤링 + 알림 발송 작업
# --------------------------------------------------
async def crawl_and_notify():
    print("🚀 크롤링 시작")
    # Repository & Service 초기화
    auction_repo = AuctionRepository(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    notif_repo = NotificationRepository(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    notifier = NotifierService(
        slack_token=settings.SLACK_TOKEN, telegram_api_key=settings.TELEGRAM_BOT_API_KEY
    )

    crawler = CrawlerService(auction_repo)
    notification_service = NotificationService(notif_repo, auction_repo, notifier)

    detect_target = [{"sido_code": "26", "sigu_code": "350"}]

    # ✅ 클래스의 인스턴스 메서드 호출
    new_auctions, updated_auctions = crawler.crawl_new_auctions(detect_target)

    if new_auctions:
        print(f"📥 신규 매물 {len(new_auctions)}건 저장 중...")
        auction_repo.insert_many(new_auctions)
        await notification_service.process_new_auctions(new_auctions)

    if updated_auctions:
        print(f"♻️ 업데이트된 매물 {len(updated_auctions)}건 갱신 중...")
        for auction in updated_auctions:
            auction_repo.update_by_id(auction, auction["id"])

    print("✅ 크롤링 및 알림 완료")


# --------------------------------------------------
# ✅ APScheduler 설정 (매주 월/목 오전 10시)
# --------------------------------------------------
scheduler = AsyncIOScheduler(timezone="Asia/Seoul")
scheduler.add_job(
    crawl_and_notify,
    trigger="cron",
    day_of_week="mon,thu",
    hour=10,
    minute=0,
)
scheduler.start()


# --------------------------------------------------
# ✅ FastAPI 시작 시 로그
# --------------------------------------------------
@app.on_event("startup")
async def startup_event():
    await crawl_and_notify()
    print("🚀 FastAPI server started and Telegram Webhook active.")
    print("🕓 Scheduler running every Monday and Thursday at 10:00 AM (KST).")
