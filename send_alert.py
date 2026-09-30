import os
import requests
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

load_dotenv()

def send_reminder():
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        return

    # 본인의 채널 아이디
    chat_ids = ["-1002594231078"] 
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    
    # 1. 한국 시간 가져오기
    kst = timezone(timedelta(hours=9))
    now = datetime.now(kst).strftime("%Y년 %m월 %d일 %H:%M")

    # 2. 날씨 정보 가져오기 (지역 이름 없이 이모지와 온도만 추출)
    try:
        weather = requests.get("https://wttr.in/Geumcheon-gu?format=%c+%t", timeout=5).text.strip()
    except:
        weather = "날씨 정보 없음"
    
    # 3. 메시지 조립 (제목 아래에 두꺼운 글씨로 시간과 날씨 추가)
    msg = f"🔔 <b>Crypto Manager 정기 알림</b>\n"
    msg += f"<b>🕒 {now} | {weather}</b>\n\n"
    msg += "대시보드를 눌러 현재 시장 지표와 포지션 현황을 확인해주세요.\n"
    
    # 본인의 미니앱 주소
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