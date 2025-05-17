import requests
import time
import hmac
import hashlib
import numpy as np
import os

API_KEY = os.getenv("BINGX_API_KEY")
API_SECRET = os.getenv("BINGX_API_SECRET")
BASE_URL = "https://open-api.bingx.com"

TRADE_AMOUNT = 15  # USDT
INTERVAL = "1h"    # 時間間隔

def get_all_symbols():
    url = f"{BASE_URL}/openApi/swap/v2/quote/contracts"
    try:
        res = requests.get(url)
        data = res.json()
        return [item['symbol'] for item in data.get('data', [])]
    except Exception as e:
        print("Error fetching symbols:", e)
        return []

def get_klines(symbol):
    url = f"{BASE_URL}/openApi/swap/v2/quote/klines?symbol={symbol}&interval={INTERVAL}&limit=100"
    try:
        res = requests.get(url).json()
        return res.get("data", [])
    except Exception as e:
        print(f"Error getting klines for {symbol}: {e}")
        return []

def calculate_indicators(prices):
    closes = []
    for c in prices:
        if isinstance(c, list) and len(c) > 4:
            try:
                closes.append(float(c[4]))
            except:
                continue

    closes = np.array(closes)
    if len(closes) < 20:
        return None

    sma_short = np.mean(closes[-5:])
    sma_long = np.mean(closes[-20:])

    return sma_short, sma_long

def sign(params, secret):
    query = "&".join([f"{k}={params[k]}" for k in sorted(params)])
    return hmac.new(secret.encode(), query.encode(), hashlib.sha256).hexdigest()

def place_order(symbol, side):
    timestamp = int(time.time() * 1000)
    endpoint = "/openApi/swap/v2/trade/order"
    url = f"{BASE_URL}{endpoint}"

    params = {
        "symbol": symbol,
        "side": side,
        "price": "",  # 市價單不需填價格
        "quantity": "",  # 這裡我們以 notional 設定
        "notional": str(TRADE_AMOUNT),
        "tradeType": "LONG" if side == "BUY" else "SHORT",
        "action": "Open",
        "timestamp": str(timestamp),
        "recvWindow": "5000"
    }

    params["signature"] = sign(params, API_SECRET)
    headers = {"X-BX-APIKEY": API_KEY}
    response = requests.post(url, data=params, headers=headers)
    print(f"Order response for {symbol}: {response.text}")

def run():
    symbols = get_all_symbols()
    for symbol in symbols:
        prices = get_klines(symbol)
        if not prices:
            continue

        result = calculate_indicators(prices)
        if not result:
            continue

        sma_short, sma_long = result

        if sma_short > sma_long:
            place_order(symbol, "BUY")
        elif sma_short < sma_long:
            place_order(symbol, "SELL")
        time.sleep(1)  # 防止過快觸發 API 限速

if __name__ == "__main__":
    run()
