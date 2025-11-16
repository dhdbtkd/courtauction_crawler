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

# 기본 감시 대상 선언
DEFAULT_DETECT_TARGET = [
    {"sido_code": "26", "sigu_code": "350"},  # 해운대구
    {"sido_code": "26", "sigu_code": "260"},  # 동래구
    {"sido_code": "26", "sigu_code": "320"},  # 북구
]


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

    auction_repo = AuctionRepository(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    notif_repo = NotificationRepository(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    notifier = NotifierService(
        slack_token=settings.SLACK_TOKEN, telegram_api_key=settings.TELEGRAM_BOT_API_KEY
    )

    crawler = CrawlerService(auction_repo)
    notification_service = NotificationService(notif_repo, auction_repo, notifier)

    # ------------------------------------------------------
    # 1) DB rules 불러오기
    # ------------------------------------------------------
    res = (
        supabase.table("notification_rules")
        .select("sido_code, sigu_code")
        .eq("enabled", True)
        .not_.is_("sido_code", None)
        .not_.is_("sigu_code", None)
        .execute()
    )

    rules = res.data or []

    # ------------------------------------------------------
    # 2) 기본 값 + DB 값 통합
    # ------------------------------------------------------
    merged = set()

    for item in DEFAULT_DETECT_TARGET:
        merged.add((item["sido_code"], item["sigu_code"]))

    for rule in rules:
        merged.add((str(rule["sido_code"]), str(rule["sigu_code"])))

    # ------------------------------------------------------
    # 3) prefix 제거
    # ------------------------------------------------------
    detect_target = []
    for sido, sigu in merged:
        sido_str = str(sido)
        sigu_str = str(sigu)

        # prefix 제거
        if sigu_str.startswith(sido_str):
            sigu_str = sigu_str[len(sido_str) :]

        # 0 방어로직 (정상 sigu_code는 3~4자리)
        if sigu_str in ["0", "", "00", "000"]:
            print(f"⚠️ 잘못된 sigu_code 감지됨 → SKIP: sido={sido_str}, sigu={sigu_str}")
            continue

        detect_target.append({"sido_code": sido_str, "sigu_code": sigu_str})

    print("📌 실제 감시 대상:", detect_target)

    # ------------------------------------------------------
    # 4) 각 지역별 순차 크롤링 (IP Ban 방지)
    # ------------------------------------------------------
    for idx, target in enumerate(detect_target):
        print(f"🔎 [{idx + 1}/{len(detect_target)}] 지역 조회: {target}")

        unit_target = [target]

        # 지역별 크롤 실행
        new_auctions, updated_auctions = crawler.crawl_new_auctions(unit_target)

        # --- 신규 저장 ---
        if new_auctions:
            print(f"📥 지역 신규 매물 {len(new_auctions)}건 저장")
            auction_repo.insert_many(new_auctions)
            await notification_service.process_new_auctions(new_auctions)

        # --- 업데이트 저장 ---
        if updated_auctions:
            print(f"♻️ 지역 업데이트 매물 {len(updated_auctions)}건 갱신")
            for auction in updated_auctions:
                auction_repo.update_by_id(auction, auction["id"])

        print("⏳ 다음 지역 조회 전 2분 대기...")
        await asyncio.sleep(120)

    print("✅ 전체 크롤링 종료")


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
