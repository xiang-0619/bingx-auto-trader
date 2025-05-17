import os
import time
import requests
import pandas as pd
import pandas_ta as ta

API_KEY = os.getenv('BINGX_API_KEY')
SECRET_KEY = os.getenv('BINGX_SECRET_KEY')
BASE_URL = "https://api.bingx.com"

TRADE_AMOUNT = 10  # 每單 10 USDT

def get_symbols():
    url = f"{BASE_URL}/api/v1/market/getAllContracts"
    response = requests.get(url)
    data = response.json()
    return [item['symbol'] for item in data['data'] if 'USDT' in item['symbol']]

def get_klines(symbol, interval="15m", limit=100):
    url = f"{BASE_URL}/api/v1/market/kline"
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    response = requests.get(url, params=params)
    data = response.json()
    if data['code'] != 0 or 'data' not in data:
        return None
    df = pd.DataFrame(data['data'])
    df.columns = ["timestamp", "open", "high", "low", "close", "volume"]
    df = df.astype(float)
    return df

def apply_strategy(df):
    df['EMA20'] = ta.ema(df['close'], length=20)
    df['EMA50'] = ta.ema(df['close'], length=50)
    macd = ta.macd(df['close'])
    df['MACD_hist'] = macd['MACDh_12_26_9']
    df['RSI'] = ta.rsi(df['close'], length=14)

    latest = df.iloc[-1]
    prev = df.iloc[-2]

    # 條件：EMA 多頭排列 + RSI 回升 + MACD 柱轉正 + 波動過濾
    ema_trend = latest['EMA20'] > latest['EMA50']
    rsi_rebound = latest['RSI'] > prev['RSI'] and latest['RSI'] < 70
    macd_turn_green = latest['MACD_hist'] > 0 and prev['MACD_hist'] < 0
    volatility = (latest['high'] - latest['low']) / latest['low'] > 0.01  # 波動 > 1%

    return ema_trend and rsi_rebound and macd_turn_green and volatility

def place_order(symbol):
    print(f"✅ 符合條件，下單：{symbol}，金額：{TRADE_AMOUNT} USDT")
    # 真實下單邏輯可在這裡實作（根據 BingX API）

def main():
    symbols = get_symbols()
    print(f"檢查 {len(symbols)} 個幣種...")

    for symbol in symbols:
        try:
            df = get_klines(symbol)
            if df is None or len(df) < 50:
                continue

            if apply_strategy(df):
                place_order(symbol)

            time.sleep(0.2)  # 降低 API 請求速率

        except Exception as e:
            print(f"⚠️ 分析 {symbol} 發生錯誤: {e}")

if __name__ == "__main__":
    main()