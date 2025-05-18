import os
import time
import requests
import hmac
import hashlib
import pandas as pd
import ta
from datetime import datetime

# 基本參數設定
API_KEY = os.getenv("BINGX_API_KEY")
SECRET_KEY = os.getenv("BINGX_SECRET_KEY")
BASE_URL = "https://open-api.bingx.com"

TRADE_AMOUNT = 10  # 每筆下單金額（USDT）
INTERVAL = "15m"   # K 線週期
SYMBOLS = ["BTC-USDT", "ETH-USDT", "XRP-USDT", "SOL-USDT", "LTC-USDT"]  # 可依需求擴充

# 停利停損設定
TP_BASE = 1.5  # 初始停利 1.5%
TP_TRAIL = 0.5 # 回撤 0.5% 就平倉
SL_THRESHOLD = -1.5  # 固定停損 -1.5%

open_positions = {}

# ---------- 工具函式 ----------

def get_signature(params, secret):
    query_string = "&".join([f"{k}={v}" for k, v in sorted(params.items())])
    return hmac.new(secret.encode(), query_string.encode(), hashlib.sha256).hexdigest()

def get_kline(symbol, interval="15m", limit=100):
    url = f"{BASE_URL}/openApi/swap/v2/quote/kline"
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    response = requests.get(url, params=params)
    return pd.DataFrame(response.json()["data"])

def get_account_position(symbol):
    timestamp = str(int(time.time() * 1000))
    params = {
        "timestamp": timestamp,
        "symbol": symbol,
    }
    signature = get_signature(params, SECRET_KEY)
    headers = {"X-BX-APIKEY": API_KEY}
    params["signature"] = signature
    url = f"{BASE_URL}/openApi/swap/v2/trade/position"
    response = requests.get(url, params=params, headers=headers)
    return response.json()

def place_order(symbol, side, price=None):
    print(f"下單請求：{symbol} {side}")
    return True  # 可改為真實下單邏輯

def close_order(symbol, positionSide):
    print(f"平倉請求：{symbol} {positionSide}")
    return True  # 可改為真實平倉邏輯

# ---------- 技術指標邏輯 ----------

def check_signal(df):
    df['EMA_FAST'] = ta.trend.ema_indicator(df['close'], window=8)
    df['EMA_SLOW'] = ta.trend.ema_indicator(df['close'], window=21)
    macd = ta.trend.macd_diff(df['close'])
    rsi = ta.momentum.rsi(df['close'], window=14)

    last_macd = macd.iloc[-1]
    prev_macd = macd.iloc[-2]
    last_rsi = rsi.iloc[-1]
    last_close = df['close'].iloc[-1]
    last_ema_fast = df['EMA_FAST'].iloc[-1]
    last_ema_slow = df['EMA_SLOW'].iloc[-1]

    long_signal = (
        last_macd > 0 and prev_macd < 0 and
        last_rsi > 50 and
        last_ema_fast > last_ema_slow
    )

    short_signal = (
        last_macd < 0 and prev_macd > 0 and
        last_rsi < 50 and
        last_ema_fast < last_ema_slow
    )

    return "BUY" if long_signal else "SELL" if short_signal else None

# ---------- 移動停利檢查 ----------

def evaluate_position(symbol, entry_price, current_price):
    change_pct = (current_price - entry_price) / entry_price * 100
    if symbol not in open_positions:
        open_positions[symbol] = {"entry": entry_price, "max_profit": change_pct}
        return None

    max_profit = open_positions[symbol]["max_profit"]
    if change_pct > max_profit:
        open_positions[symbol]["max_profit"] = change_pct

    if change_pct <= -SL_THRESHOLD:
        return "STOP_LOSS"
    elif change_pct >= TP_BASE and change_pct <= (max_profit - TP_TRAIL):
        return "TRAIL_TP"

    return None

# ---------- 主邏輯 ----------

def main():
    for symbol in SYMBOLS:
        try:
            df = get_kline(symbol, interval=INTERVAL)
            df['close'] = df['close'].astype(float)
            signal = check_signal(df)

            if signal:
                position = get_account_position(symbol)
                has_position = "data" in position and position["data"] and float(position["data"]["positionAmt"]) != 0

                if not has_position:
                    place_order(symbol, "BUY" if signal == "BUY" else "SELL")
                    open_positions[symbol] = {
                        "entry": df['close'].iloc[-1],
                        "max_profit": 0
                    }

            # 檢查平倉條件
            if symbol in open_positions:
                current_price = df['close'].iloc[-1]
                entry_price = open_positions[symbol]["entry"]
                exit_reason = evaluate_position(symbol, entry_price, current_price)

                if exit_reason:
                    close_order(symbol, "LONG" if signal == "BUY" else "SHORT")
                    del open_positions[symbol]

        except Exception as e:
            print(f"[錯誤] {symbol}: {e}")

if __name__ == "__main__":
    main()