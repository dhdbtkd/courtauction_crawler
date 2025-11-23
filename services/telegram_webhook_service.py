# telegram_webhook.py
from fastapi import FastAPI, Request
from supabase import create_client
import requests
import os

from config.settings import settings

app = FastAPI()

supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)


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
        print("⚠️ Missing chat_id or text.")
        return {"ok": False}

    # ✅ /start 명령 처리
    if text.startswith("/start"):
        parts = text.split(" ")
        if len(parts) < 2:
            await send_message(
                chat_id,
                "❌ 인증 토큰이 없습니다.\n웹사이트에서 '텔레그램 연동하기' 버튼을 다시 눌러주세요.",
            )
            return {"ok": True}

        token = parts[1].strip()
        print(f"🔑 Received /start token: {token}")

        # Supabase에서 user_id 찾기
        res = (
            supabase.table("users")
            .select("id, email")
            .eq("telegram_auth_token", token)
            .single()
            .execute()
        )

        if not res.data:
            await send_message(chat_id, "❌ 잘못된 토큰입니다. 다시 시도해주세요.")
            print("❌ Invalid token:", token)
            return {"ok": True}

        user_id = res.data["id"]
        email = res.data["email"]

        # ✅ notification_channels에 등록 (Upsert)
        supabase.table("notification_channels").upsert(
            {
                "user_id": user_id,
                "type": "telegram",
                "identifier": chat_id,
                "enabled": True,
            }
        ).execute()

        # ✅ 사용된 토큰 비우기 (재사용 방지)
        supabase.table("users").update({"telegram_auth_token": None}).eq(
            "id", user_id
        ).execute()

        # ✅ 성공 메시지 전송
        await send_message(
            chat_id,
            f"✅ 텔레그램 알림이 성공적으로 연결되었습니다!\n\n계정: {email}\n\n이제 경매 알림을 받아볼 수 있습니다.\n페이지로 돌아가서 새로고침해주세요.",
        )

        print(f"✅ Telegram linked successfully → user={email}, chat_id={chat_id}")
        return {"ok": True}

    # ✅ 기타 명령어 처리
    await send_message(
        chat_id,
        "🤖 명령어를 인식하지 못했습니다.\n/start 명령으로 인증을 다시 진행해주세요.",
    )
    return {"ok": True}


async def send_message(chat_id: str, text: str):
    """텔레그램으로 메시지 보내기"""
    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_API_KEY}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    try:
        requests.post(url, data=payload)
    except Exception as e:
        print("⚠️ Telegram send_message error:", e)
