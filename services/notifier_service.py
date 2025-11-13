import requests
import asyncio
import aiohttp


class NotifierService:
    def __init__(self, slack_token: str = None, telegram_api_key: str = None):
        self.slack_token = slack_token
        self.telegram_api_key = telegram_api_key

    # ✅ Slack 메시지 발송
    async def send_slack_message(self, channel: str, text: str):
        if not self.slack_token:
            print("⚠️ Slack 토큰이 설정되지 않았습니다.")
            return

        url = "https://slack.com/api/chat.postMessage"
        headers = {"Authorization": f"Bearer {self.slack_token}"}
        payload = {"channel": channel, "text": text}

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None, lambda: requests.post(url, headers=headers, json=payload)
        )
        print(f"📤 Slack 메시지 전송 완료 → {channel}")

    # ✅ Telegram 메시지 발송
    async def send_telegram_message(self, chat_id, text, image_url=None):
        base_url = f"https://api.telegram.org/bot{self.telegram_api_key}"

        if image_url:
            url = f"{base_url}/sendPhoto"
            payload = {
                "chat_id": chat_id,
                "photo": image_url,
                "caption": text,
                "parse_mode": "Markdown",
            }
        else:
            url = f"{base_url}/sendMessage"
            payload = {
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "Markdown",
            }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as resp:
                if resp.status != 200:
                    print(f"❌ Telegram 전송 실패: {resp.status}")
