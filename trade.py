import os
import time
import hmac
import hashlib
import json
import requests
import pandas as pd
import pandas_ta as ta

API_KEY = os.getenv('BINGX_API_KEY')
SECRET_KEY = os.getenv('BINGX_SECRET_KEY')
BASE_URL = "https://api.bingx.com"

TRADE_AMOUNT = 10  # 每單 10 USDT

def sign_request(params: dict, secret: str):
    """BingX API 簽名"""
    query = '&'.join([f"{k}={params[k]}" for k in sorted(params)])
    return hmac.new(secret.encode(), query.encode(), hashlib.sha256).hexdigest()

def get_symbols():
    url = f"{BASE_URL}/api/v1/market/getAllContracts"
    response = requests.get(url)
    data = response.json()
    if data.get("code") != 0:
        print("❌ 取得幣種失敗:", data)
        return []
    return [item['symbol'] for item in data['data'] if 'USDT' in item['symbol']]

def get_klines(symbol, interval="15m", limit=100):
    url = f"{BASE_URL}/api/v1/market/kline"
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    response = requests.get(url, params=params)
    data = response.json()
    if data.get('code') != 0 or 'data' not in data:
        print(f"❌ 取得 {symbol} K 線失敗")
        return None
    df = pd.DataFrame(data['data'])
    df.columns = ["timestamp", "open", "high", "low", "close", "volume"]
    df = df.astype(float)
    return df

def get_max_leverage(symbol):
    url = f"{BASE_URL}/api/v1/futures/max_leverage?symbol={symbol}"
    try:
        resp = requests.get(url)
        data = resp.json()
        if data.get("code") == 0 and "data" in data:
            return int(data["data"].get("maxLeverage", 20))
    except Exception as e:
        print(f"⚠️ 取得槓桿錯誤: {e}")
    return 20  # 預設20倍

def place_order(symbol, side, amount_usdt):
    path = "/api/v1/futures/order"
    timestamp = int(time.time() * 1000)

    leverage = get_max_leverage(symbol)

    params = {
        "symbol": symbol,
        "side": side,
        "type": "MARKET",
        "quantity": amount_usdt,
        "timestamp": timestamp,
        "leverage": leverage
    }
    params["signature"] = sign_request(params, SECRET_KEY)

    headers = {
        "X-BX-APIKEY": API_KEY,
        "Content-Type": "application/json"
    }

    url = BASE_URL + path
    resp = requests.post(url, headers=headers, data=json.dumps(params))
    result = resp.json()

    if resp.status_code == 200 and result.get("code") == 0:
        print(f"✅ 下單成功: {symbol} {side} {amount_usdt} USDT 槓桿 {leverage}倍")
    else:
        print(f"❌ 下單失敗: {result}")

def apply_strategy(df):
    df['EMA20'] = ta.ema(df['close'], length=20)
    df['EMA50'] = ta.ema(df['close'], length=50)
    macd = ta.macd(df['close'])
    df['MACD_hist'] = macd['MACDh_12_26_9']
    df['RSI'] = ta.rsi(df['close'], length=14)

    latest = df.iloc[-1]
    prev = df.iloc[-2]

    ema_trend = latest['EMA20'] > latest['EMA50']
    rsi_rebound = latest['RSI'] > prev['RSI'] and latest['RSI'] < 70
    macd_turn_green = latest['MACD_hist'] > 0 and prev['MACD_hist'] < 0
    volatility = (latest['high'] - latest['low']) / latest['low'] > 0.01

    if ema_trend and rsi_rebound and macd_turn_green and volatility:
        return "BUY"
    else:
        # 這裡改成做空訊號，也可以改成 None 跳過
        return "SELL"

def main():
    symbols = get_symbols()
    print(f"開始檢查 {len(symbols)} 個幣種...")

    for symbol in symbols:
        try:
            df = get_klines(symbol)
            if df is None or len(df) < 50:
                continue

            signal = apply_strategy(df)
            if signal in ["BUY", "SELL"]:
                place_order(symbol, signal, TRADE_AMOUNT)

            time.sleep(0.2)

        except Exception as e:
            print(f"⚠️ 分析 {symbol} 時發生錯誤: {e}")

if __name__ == "__main__":
    main()