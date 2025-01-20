from telegram.ext import Updater, CommandHandler
from telegram.error import TelegramError
import telegram
import asyncio
from typing import Union, Optional

class TelegramNotifier:
    def __init__(self, token : str, chat_id : Union[str, int]):
        self.bot = telegram.Bot(token)
        self.chat_id = chat_id
    def start(update, context):
        """봇이 /start 명령어를 받았을 때 실행되는 함수"""
        update.message.reply_text('안녕하세요! 메시지 전송 봇입니다.')

    def send_message(self, message):
        self.bot.send_message(chat_id=self.chat_id, text=message)

    async def send_photo(self, photo, caption):
        """
        사진 전송
        
        Args:
            photo (Union[str, bytes]): 파일 경로나 바이트 형태의 사진
            caption (Optional[str]): 사진과 함께 보낼 설명 텍스트
            
        Returns:
            bool: 전송 성공 여부
        """
        try:
            message = await self.bot.send_photo(
                chat_id=self.chat_id,
                photo=photo,
                caption=caption,
                parse_mode="Markdown",
            )
            if message and message.photo:
                print("사진 전송 성공!")
                return True
        except TelegramError as e:
            print(f"사진 전송 실패: {str(e)}")
            return False