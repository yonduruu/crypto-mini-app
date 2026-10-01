import os
import requests
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

load_dotenv()

def send_reminder():
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not bot_token:
        print("❌ 에러: TELEGRAM_BOT_TOKEN 환경변수를 찾을 수 없습니다. 깃허브 Secrets 설정을 확인하세요.")
        return

    # 환경변수에 TELEGRAM_CHAT_ID가 있으면 우선 사용하고, 없으면 기본값 사용
    env_chat_id = os.getenv("TELEGRAM_CHAT_ID")
    chat_ids = [env_chat_id] if env_chat_id else ["-1002594231078"]
    
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    
    # 1. 한국 시간 가져오기
    kst = timezone(timedelta(hours=9))
    now = datetime.now(kst).strftime("%Y년 %m월 %d일 %H:%M")

    # 2. 날씨 정보 안전하게 가져오기 (에러 페이지나 HTML 태그가 오면 무시)
    weather = "날씨 정보 없음"
    try:
        w_res = requests.get("https://wttr.in/Geumcheon-gu?format=%c+%t", timeout=5)
        if w_res.status_code == 200 and "<" not in w_res.text and "Unknown" not in w_res.text:
            weather = w_res.text.strip()
    except Exception as e:
        print(f"⚠️ 날씨 조회 실패: {e}")
    
    # 3. 메시지 조립
    msg = f"🔔 <b>Crypto Manager 정기 알림</b>\n"
    msg += f"<b>🕒 {now} | {weather}</b>\n\n"
    msg += "대시보드를 눌러 현재 시장 지표와 포지션 현황을 확인해주세요.\n"
    
    # 본인의 미니앱 주소 (https 권장)
    reply_markup = {
        "inline_keyboard": [
            [{"text": "📊 대시보드 열기", "url": "https://t.me/coco1_1_bot/cocoapp"}]
        ]
    }
    
    for chat_id in chat_ids:
        payload = {
            "chat_id": chat_id,
            "text": msg,
            "parse_mode": "HTML",
            "reply_markup": reply_markup
        }
        res = requests.post(url, json=payload, timeout=5)
        if res.status_code == 200:
            print(f"✅ 텔레그램 알림 발송 성공! (Chat ID: {chat_id})")
        else:
            print(f"❌ 텔레그램 발송 실패 ({res.status_code}): {res.text}")

if __name__ == "__main__":
    send_reminder()