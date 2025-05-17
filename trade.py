import requests
import time
import hmac
import hashlib
import pandas as pd
import numpy as np
import ta
from datetime import datetime
from config import API_KEY, SECRET_KEY, BASE_URL, TRADE_AMOUNT

symbol_list_url = f"{BASE_URL}/v1/market/getAllContracts"
headers = {"X-BX-APIKEY": API_KEY}

# 測試 API 有效性
def test_api_key():
    try:
        resp = requests.get(symbol_list_url, headers=headers, timeout=10)
        if resp.status_code == 200:
            print("✅ API Key 驗證成功")
        else:
            print("❌ API Key 驗證失敗，請檢查 config.py")
            exit()
    except Exception as e:
        print("❌ API 連線失敗：", str(e))
        exit()

def get_klines(symbol):
    url = f"{BASE_URL}/v1/market/kline"
    params = {
        "symbol": symbol,
        "interval": "15m",
        "limit": 100
    }
    try:
        res = requests.get(url, params=params).json()
        if res.get("code") == 0 and res.get("data"):
            df = pd.DataFrame(res["data"])
            df.columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
            df = df.astype(float)
            return df
    except:
        pass
    return None

def calculate_indicators(df):
    df['ema5'] = ta.trend.ema_indicator(df['close'], window=5).fillna(0)
    df['ema20'] = ta.trend.ema_indicator(df['close'], window=20).fillna(0)
    df['ema50'] = ta.trend.ema_indicator(df['close'], window=50).fillna(0)
    df['rsi'] = ta.momentum.rsi(df['close'], window=14).fillna(0)
    macd = ta.trend.macd_diff(df['close']).fillna(0)
    df['macd_hist'] = macd
    df['bollinger_upper'] = ta.volatility.BollingerBands(df['close']).bollinger_hband().fillna(0)
    df['bollinger_lower'] = ta.volatility.BollingerBands(df['close']).bollinger_lband().fillna(0)
    return df

def should_long(df):
    if df is None or len(df) < 50:
        return False

    last = df.iloc[-1]
    prev = df.iloc[-2]

    # 條件組合 A
    condition_a = (
        last['ema5'] > last['ema20'] > last['ema50'] and
        prev['rsi'] < 35 and last['rsi'] > 40 and
        prev['macd_hist'] < 0 and last['macd_hist'] > 0
    )

    # 條件組合 B
    condition_b = (
        last['close'] > max(df['high'][-6:-1]) and
        last['rsi'] > 50 and
        last['macd_hist'] > 0 and
        (last['bollinger_upper'] - last['bollinger_lower']) > (df['bollinger_upper'] - df['bollinger_lower']).mean()
    )

    return condition_a or condition_b

def get_positions():
    url = f"{BASE_URL}/v1/user/positions"
    timestamp = str(int(time.time() * 1000))
    sign = hmac.new(SECRET_KEY.encode(), timestamp.encode(), hashlib.sha256).hexdigest()
    headers_signed = {
        "X-BX-APIKEY": API_KEY,
        "X-BX-SIGNATURE": sign,
        "X-BX-TIMESTAMP": timestamp
    }
    try:
        res = requests.get(url, headers=headers_signed, timeout=10).json()
        if res.get("code") == 0:
            return [p['symbol'] for p in res['data'] if p['positionAmt'] != "0"]
    except:
        pass
    return []

def place_order(symbol):
    url = f"{BASE_URL}/v1/user/submitOrder"
    timestamp = str(int(time.time() * 1000))
    body = f"symbol={symbol}&price=0&vol={TRADE_AMOUNT}&side=1&type=1&open_type=1&position_id=0&leverage=10&external_oid=auto_trade_{timestamp}&stop_loss=0&take_profit=0&position_mode=1"
    sign = hmac.new(SECRET_KEY.encode(), (body + timestamp).encode(), hashlib.sha256).hexdigest()
    headers_signed = {
        "X-BX-APIKEY": API_KEY,
        "X-BX-SIGNATURE": sign,
        "X-BX-TIMESTAMP": timestamp,
        "Content-Type": "application/x-www-form-urlencoded"
    }
    try:
        res = requests.post(url, headers=headers_signed, data=body).json()
        if res.get("code") == 0:
            print(f"✅ 開多成功: {symbol}")
        else:
            print(f"❌ 下單失敗: {symbol}, 錯誤: {res}")
    except Exception as e:
        print(f"❌ 下單異常: {symbol} => {e}")

def main():
    test_api_key()
    res = requests.get(symbol_list_url, headers=headers).json()
    if res.get("code") != 0:
        print("❌ 無法獲取幣種清單")
        return

    symbols = [s["symbol"] for s in res["data"] if "USDT" in s["symbol"]]
    opened_symbols = get_positions()

    for symbol in symbols:
        if symbol in opened_symbols:
            continue
        df = get_klines(symbol)
        if df is None:
            continue
        df = calculate_indicators(df)
        if should_long(df):
            place_order(symbol)
        time.sleep(0.5)

if __name__ == "__main__":
    main()