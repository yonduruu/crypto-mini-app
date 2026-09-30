import os
import json
import base64
from datetime import datetime
import requests
import ccxt
import feedparser
from dotenv import load_dotenv

load_dotenv()

def create_okx_client(api_key=None, secret=None, passphrase=None):
    params = {
        'enableRateLimit': True,
        'options': {'defaultType': 'swap'}
    }
    if api_key and secret and passphrase:
        params.update({
            'apiKey': api_key,
            'secret': secret,
            'password': passphrase,
        })
    return ccxt.okx(params)

def get_market_overview(public_client):
    """공포 & 탐욕 지수 및 BTC / ETH 펀딩비 수집"""
    overview = {
        "fear_greed": {"value": 50, "classification": "Neutral"},
        "funding_rates": {}
    }

    try:
        fng_res = requests.get("https://api.alternative.me/fng/?limit=1", timeout=5).json()
        if fng_res.get('data'):
            overview["fear_greed"] = {
                "value": int(fng_res['data'][0]['value']),
                "classification": fng_res['data'][0]['value_classification']
            }
    except Exception as e:
        print(f"⚠️ 공포/탐욕 지수 수집 실패: {e}")

    for symbol in ['BTC/USDT:USDT', 'ETH/USDT:USDT']:
        try:
            funding_info = public_client.fetch_funding_rate(symbol)
            rate = float(funding_info.get('fundingRate') or 0.0) * 100
            coin_name = symbol.split('/')[0]
            overview["funding_rates"][coin_name] = f"{rate:+.4f}%"
        except Exception:
            coin_name = symbol.split('/')[0]
            overview["funding_rates"][coin_name] = "N/A"

    return overview

def get_top_movers_6h(public_client, limit=10):
    """최근 6시간 변동성 상위 10개 코인 수집"""
    try:
        tickers = public_client.fetch_tickers()
        swap_tickers = [
            t for sym, t in tickers.items()
            if sym.endswith('/USDT:USDT') and t.get('baseVolume', 0) > 100000
        ]

        swap_tickers.sort(key=lambda x: float(x.get('quoteVolume') or 0.0), reverse=True)
        candidates = swap_tickers[:35]

        movers = []
        for t in candidates:
            sym = t['symbol']
            try:
                ohlcv = public_client.fetch_ohlcv(sym, timeframe='1h', limit=7)
                if len(ohlcv) >= 7:
                    price_6h_ago = ohlcv[0][1]
                    current_price = ohlcv[-1][4]
                    if price_6h_ago > 0:
                        change_pct = ((current_price - price_6h_ago) / price_6h_ago) * 100
                        clean_sym = sym.split('/')[0]
                        movers.append({
                            "symbol": clean_sym,
                            "change_pct": change_pct,
                            "current_price": current_price
                        })
            except Exception:
                continue

        movers.sort(key=lambda x: abs(x['change_pct']), reverse=True)
        return movers[:limit]

    except Exception as e:
        print(f"⚠️ 변동성 랭킹 수집 실패: {e}")
        return []

def translate_to_korean(text):
    """무료 오픈 번역 API (MyMemory) 기반 안정적인 한국어 번역"""
    if not text:
        return ""
    
    # 1. MyMemory 오픈 번역 API
    try:
        url = "https://api.mymemory.translated.net/get"
        params = {
            "q": text,
            "langpair": "en|ko"
        }
        res = requests.get(url, params=params, timeout=5)
        if res.status_code == 200:
            data = res.json()
            translated = data.get("responseData", {}).get("translatedText")
            # 정상적인 번역 결과이고 원문과 다른 경우
            if translated and translated.strip() and translated.lower() != text.lower():
                return translated
    except Exception as e:
        pass

    # 2. 백업: Google Web 번역
    try:
        url = "https://translate.googleapis.com/translate_a/single"
        params = {
            "client": "gtx",
            "sl": "auto",
            "tl": "ko",
            "dt": "t",
            "q": text
        }
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, params=params, headers=headers, timeout=5)
        if res.status_code == 200:
            data = res.json()
            translated = "".join([part[0] for part in data[0] if part and part[0]])
            if translated:
                return translated
    except Exception:
        pass

    return text

def get_crypto_news(limit=5):
    """암호화폐 글로벌 속보 수집 및 실시간 한국어 번역"""
    news_list = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }
    
    feed_urls = [
        "https://cointelegraph.com/rss",
        "https://decrypt.co/feed"
    ]
    
    for url in feed_urls:
        try:
            res = requests.get(url, headers=headers, timeout=6)
            if res.status_code == 200:
                feed = feedparser.parse(res.content)
                for entry in feed.entries[:limit]:
                    published_parsed = entry.get('published_parsed')
                    time_str = datetime(*published_parsed[:6]).strftime("%m-%d %H:%M") if published_parsed else ""
                    raw_title = entry.get('title', '')

                    # 한국어 번역 실행
                    title_ko = translate_to_korean(raw_title)

                    news_list.append({
                        "title": raw_title,
                        "title_ko": title_ko,
                        "link": entry.get('link', ''),
                        "published": time_str
                    })
                if news_list:
                    break
        except Exception as e:
            print(f"⚠️ RSS ({url}) 수집 에러: {e}")
            continue

    return news_list[:limit]

def get_account_data(client, user_name):
    """노꾸리/욘두루 선물 포지션, 현물 자산 및 개별 펀딩비 수집"""
    if not client:
        return {"user": user_name, "status": "FAIL", "positions": [], "spot": []}

    try:
        raw_positions = client.fetch_positions()
        active_positions = []

        for item in raw_positions:
            info = item.get('info', {})
            raw_pos = float(info.get('pos') or 0.0)
            ccxt_contracts = float(item.get('contracts') or 0.0)

            if raw_pos != 0 or ccxt_contracts > 0:
                symbol = item.get('symbol') or info.get('instId', 'UNKNOWN')
                pos_side = info.get('posSide', 'net').lower()
                if pos_side == 'long':
                    side = 'LONG'
                elif pos_side == 'short':
                    side = 'SHORT'
                else:
                    side = 'LONG' if raw_pos > 0 else 'SHORT'

                entry_price = float(item.get('entryPrice') or info.get('avgPx') or 0.0)
                mark_price = float(item.get('markPrice') or info.get('markPx') or item.get('last') or 0.0)
                pnl_ratio = float(info.get('uplRatio') or 0.0)
                pnl_pct = pnl_ratio * 100 if pnl_ratio != 0 else float(item.get('percentage') or 0.0)
                unrealized_pnl = float(item.get('unrealizedPnl') or info.get('upl') or 0.0)
                leverage = info.get('lever', '1')

                # [추가] 진입 중인 코인의 실시간 펀딩비 개별 조회
                funding_rate = 0.0
                try:
                    fund_info = client.fetch_funding_rate(symbol)
                    funding_rate = float(fund_info.get('fundingRate') or 0.0) * 100
                except Exception as e:
                    print(f"⚠️ {symbol} 펀딩비 조회 실패: {e}")

                active_positions.append({
                    'symbol': symbol,
                    'side': side,
                    'leverage': leverage,
                    'entry_price': entry_price,
                    'mark_price': mark_price,
                    'pnl_pct': pnl_pct,
                    'unrealized_pnl': unrealized_pnl,
                    'funding_rate': funding_rate  # 펀딩비 데이터 추가
                })

        bal_res = client.private_get_account_balance()
        spot_assets = []
        details = bal_res.get('data', [{}])[0].get('details', [])

        for b in details:
            coin = b.get('ccy')
            equity = float(b.get('eq') or 0.0)
            usd_val = float(b.get('eqUsd') or 0.0)

            if usd_val >= 1.0:
                spot_assets.append({
                    'coin': coin,
                    'amount': equity,
                    'usd_val': usd_val
                })

        spot_assets.sort(key=lambda x: x['usd_val'], reverse=True)

        return {
            "user": user_name,
            "status": "SUCCESS",
            "positions": active_positions,
            "spot": spot_assets
        }

    except Exception as e:
        return {"user": user_name, "status": "ERROR", "message": str(e), "positions": [], "spot": []}

    
def upload_to_github(data_content, file_path="data.json"):
    """GitHub API를 통한 data.json 원격 자동 업로드"""
    token = os.getenv("GITHUB_TOKEN")
    repo = os.getenv("GITHUB_REPO")

    if not token or not repo:
        print("⚠️ GITHUB_TOKEN 또는 GITHUB_REPO가 설정되지 않았습니다.")
        return

    url = f"https://api.github.com/repos/{repo}/contents/{file_path}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json"
    }

    sha = None
    res = requests.get(url, headers=headers)
    if res.status_code == 200:
        sha = res.json().get("sha")

    encoded_content = base64.b64encode(data_content.encode("utf-8")).decode("utf-8")
    payload = {
        "message": f"update: {file_path} auto update ({datetime.now().strftime('%H:%M:%S')})",
        "content": encoded_content
    }
    if sha:
        payload["sha"] = sha

    put_res = requests.put(url, headers=headers, json=payload)
    if put_res.status_code in [200, 201]:
        print("🚀 GitHub API로 data.json 자동 업로드 완료!")
    else:
        print(f"❌ 업로드 실패 ({put_res.status_code}): {put_res.text}")

if __name__ == "__main__":
    public_client = create_okx_client()
    client_a = create_okx_client(
        os.getenv('USER_A_API_KEY'),
        os.getenv('USER_A_SECRET'),
        os.getenv('USER_A_PASSPHRASE')
    )
    client_b = create_okx_client(
        os.getenv('USER_B_API_KEY'),
        os.getenv('USER_B_SECRET'),
        os.getenv('USER_B_PASSPHRASE')
    )

    print("1. 시장 심리 및 펀딩비 수집 중...")
    market_overview = get_market_overview(public_client)

    print("2. 최근 6시간 급변동 코인 TOP 10 계산 중...")
    top_movers = get_top_movers_6h(public_client, limit=10)

    print("3. 최신 코인 속보 뉴스 수집 및 한국어 번역 중...")
    latest_news = get_crypto_news(limit=5)
    for idx, n in enumerate(latest_news, 1):
        print(f"   [{idx}] 번역: {n['title_ko']}")

    print("4. 노꾸리 & 욘두루 계좌 데이터 수집 중...")
    res_a = get_account_data(client_a, "노꾸리")
    res_b = get_account_data(client_b, "욘두루")

    dashboard_data = {
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "market": market_overview,
        "movers_6h": top_movers,
        "news": latest_news,
        "accounts": [res_a, res_b]
    }

    json_str = json.dumps(dashboard_data, ensure_ascii=False, indent=2)

    with open("data.json", "w", encoding="utf-8") as f:
        f.write(json_str)
    print("📁 data.json 생성 완료")

    upload_to_github(json_str, "data.json")