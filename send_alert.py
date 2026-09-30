import os
import requests
from dotenv import load_dotenv

load_dotenv()

def send_reminder():
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        return

    # 👇 채널 아이디와 미니앱 주소는 본인 것으로 다시 채워주세요!
    chat_ids = ["-1002594231078"] 
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    
    msg = "🔔 <b>포트폴리오 정기 알림</b>\n\n대시보드를 눌러 현재 시장 지표와 포지션 현황을 확인해주세요.\n"
    
    reply_markup = {
        "inline_keyboard": [
            [{"text": "📊 대시보드 열기", "url": "http://t.me/coco1_1_bot/cocoapp"}]
        ]
    }
    
    for chat_id in chat_ids:
        payload = {
            "chat_id": chat_id,
            "text": msg,
            "parse_mode": "HTML",
            "reply_markup": reply_markup
        }
        requests.post(url, json=payload, timeout=5)

if __name__ == "__main__":
    send_reminder()