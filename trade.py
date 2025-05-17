import requests
import time
import hmac
import hashlib
import os

# 如果你是使用 GitHub Actions 的話，就從環境變數中讀取
API_KEY = os.environ.get("BINGX_API_KEY")
SECRET_KEY = os.environ.get("BINGX_SECRET_KEY")
BASE_URL = 'https://open-api.bingx.com'

def sign_request(params, secret):
    query_string = '&'.join([f"{key}={params[key]}" for key in sorted(params)])
    signature = hmac.new(secret.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()
    return signature

def test_api_key():
    timestamp = int(time.time() * 1000)
    params = {
        "timestamp": timestamp
    }
    params["signature"] = sign_request(params, SECRET_KEY)

    headers = {
        "X-BX-APIKEY": API_KEY
    }

    try:
        response = requests.get(f"{BASE_URL}/openApi/swap/v2/user/balance", headers=headers, params=params)
        print("✅ API 測試結果：", response.status_code, response.text)
    except Exception as e:
        print("❌ API 測試錯誤：", str(e))

# 執行 API 測試
test_api_key()
import os
import time
import requests
import hmac
import hashlib
import pandas as pd
import numpy as np
import ta

# 環境變數設定（來自 GitHub Secrets）
API_KEY = os.getenv("BINGX_API_KEY")
SECRET_KEY = os.getenv("BINGX_SECRET_KEY")
BASE_URL = os.getenv("BINGX_BASE_URL", "https://api.bingx.com")
TRADE_AMOUNT = float(os.getenv("TRADE_AMOUNT", 10))

INTERVAL = "15m"
LIMIT = 100
HEADERS = {"X-BX-APIKEY": API_KEY}

def sign(params: dict):
    query_string = "&".join([f"{key}={params[key]}" for key in sorted(params)])
    signature = hmac.new(SECRET_KEY.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()
    return signature

def get_klines(symbol: str):
    url = f"{BASE_URL}/v1/market/kline"
    params = {
        "symbol": symbol,
        "interval": INTERVAL,
        "limit": LIMIT
    }
    try:
        response = requests.get(url, params=params)
        data = response.json()
        if "data" in data:
            df = pd.DataFrame(data["data"])
            df["open"] = df["open"].astype(float)
            df["high"] = df["high"].astype(float)
            df["low"] = df["low"].astype(float)
            df["close"] = df["close"].astype(float)
            df["volume"] = df["volume"].astype(float)
            return df
        else:
            return None
    except:
        return None

def technical_signal(df):
    df["ema20"] = ta.trend.ema_indicator(df["close"], window=20).fillna(0)
    df["ema50"] = ta.trend.ema_indicator(df["close"], window=50).fillna(0)
    df["macd_hist"] = ta.trend.macd_diff(df["close"]).fillna(0)
    df["rsi"] = ta.momentum.rsi(df["close"], window=14).fillna(0)

    ema_bullish = df["ema20"].iloc[-1] > df["ema50"].iloc[-1]
    macd_positive = df["macd_hist"].iloc[-1] > 0 and df["macd_hist"].iloc[-2] <= 0
    rsi_rebound = df["rsi"].iloc[-1] > df["rsi"].iloc[-2] and df["rsi"].iloc[-1] > 40

    return ema_bullish and macd_positive and rsi_rebound

def place_order(symbol: str):
    timestamp = int(time.time() * 1000)
    params = {
        "symbol": symbol,
        "side": "BUY",
        "type": "MARKET",
        "quantity": TRADE_AMOUNT,
        "timestamp": timestamp
    }
    params["signature"] = sign(params)
    url = f"{BASE_URL}/v1/user/contract/order"
    try:
        response = requests.post(url, headers=HEADERS, params=params)
        print(f"Order placed for {symbol}: {response.text}")
    except Exception as e:
        print(f"Order failed for {symbol}: {str(e)}")

def get_all_symbols():
    url = f"{BASE_URL}/v1/market/getAllContracts"
    try:
        response = requests.get(url)
        data = response.json()
        return [s["symbol"] for s in data.get("data", []) if "USDT" in s["symbol"]]
    except:
        return []

def main():
    symbols = get_all_symbols()
    for symbol in symbols:
        df = get_klines(symbol)
        if df is not None and technical_signal(df):
            place_order(symbol)

if __name__ == "__main__":
    main()