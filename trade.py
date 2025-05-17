import os
import time
import requests
import pandas as pd
import numpy as np
from datetime import datetime
from ta.trend import EMAIndicator, MACD
from ta.momentum import RSIIndicator

from config import API_KEY, SECRET_KEY, BASE_URL, TRADE_AMOUNT

INTERVAL = "15m"
LIMIT = 100
SYMBOL_LIST = []  # 留空代表自動讀取全部支持的交易對
POSITION_TRACKER = {}  # 用來追蹤目前持倉的幣

def get_symbols():
    url = f"{BASE_URL}/api/v1/market/getAllContracts"
    res = requests.get(url).json()
    return [s['symbol'] for s in res['data'] if s['contractType'] == 'linear_perpetual']

def get_klines(symbol):
    url = f"{BASE_URL}/api/v1/market/kline"
    params = {"symbol": symbol, "interval": INTERVAL, "limit": LIMIT}
    res = requests.get(url, params=params).json()
    df = pd.DataFrame(res['data'], columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df = df.astype(float)
    return df

def strategy(df):
    df['ema_20'] = EMAIndicator(df['close'], window=20).ema_indicator()
    df['ema_50'] = EMAIndicator(df['close'], window=50).ema_indicator()
    macd = MACD(df['close'])
    df['macd'] = macd.macd()
    df['macd_hist'] = macd.macd_diff()
    df['rsi'] = RSIIndicator(df['close'], window=14).rsi()

    latest = df.iloc[-1]
    prev = df.iloc[-2]

    # 條件 1: MACD 柱轉正
    cond_macd = latest['macd_hist'] > 0 and prev['macd_hist'] <= 0
    # 條件 2: RSI 回升
    cond_rsi = latest['rsi'] > prev['rsi'] and latest['rsi'] < 70
    # 條件 3: EMA 多頭排列
    cond_ema = latest['ema_20'] > latest['ema_50']
    # 條件 4: 波動幅度高（當前K棒超過平均幅度1.5倍）
    avg_range = (df['high'] - df['low']).rolling(window=20).mean().iloc[-2]
    cond_volatility = (latest['high'] - latest['low']) > 1.5 * avg_range

    return cond_macd or cond_rsi or cond_ema or cond_volatility

def has_position(symbol):
    return POSITION_TRACKER.get(symbol, False)

def set_position(symbol, status=True):
    POSITION_TRACKER[symbol] = status

def place_order(symbol, side):
    print(f"[下單] {symbol} 開倉方向: {side}")

    url = f"{BASE_URL}/api/v1/user/contract/order"
    params = {
        "symbol": symbol,
        "side": side,
        "positionSide": "LONG",
        "type": "MARKET",
        "quantity": TRADE_AMOUNT,
        "timestamp": int(time.time() * 1000),
    }
    headers = {"X-BX-APIKEY": API_KEY}
    res = requests.post(url, params=params, headers=headers)
    print(res.json())
    set_position(symbol, True)

def run():
    symbols = SYMBOL_LIST or get_symbols()
    print(f"[執行時間] {datetime.now()} - 監控交易對數量: {len(symbols)}")

    for symbol in symbols:
        try:
            if has_position(symbol):
                print(f"[略過] {symbol} 已持倉")
                continue

            df = get_klines(symbol)
            if strategy(df):
                place_order(symbol, "BUY")
            else:
                print(f"[無信號] {symbol}")
        except Exception as e:
            print(f"[錯誤] {symbol}: {e}")

if __name__ == "__main__":
    run()