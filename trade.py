import requests
import time
import hmac
import hashlib
import json
import os
import datetime
import pandas as pd
import numpy as np
import ta  # 使用 ta-lib 替代方案（技術分析）
import warnings
warnings.filterwarnings("ignore")

API_KEY = os.getenv("BINGX_API_KEY")
SECRET_KEY = os.getenv("BINGX_SECRET_KEY")
BASE_URL = "https://open-api.bingx.com"
TRADE_AMOUNT = 10  # 每單 USDT 數量

INTERVAL = "15m"
LIMIT = 100

headers = {
    "X-BX-APIKEY": API_KEY
}


def get_server_time():
    return str(int(time.time() * 1000))


def sign(params):
    query_string = '&'.join([f"{key}={params[key]}" for key in sorted(params)])
    signature = hmac.new(SECRET_KEY.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()
    return signature


def get_symbols():
    url = f"{BASE_URL}/v1/market/getAllContracts"
    response = requests.get(url).json()
    symbols = [item['symbol'] for item in response['data'] if item['quoteAsset'] == 'USDT']
    return symbols


def get_klines(symbol):
    url = f"{BASE_URL}/v1/market/kline"
    params = {
        "symbol": symbol,
        "interval": INTERVAL,
        "limit": LIMIT
    }
    response = requests.get(url, params=params).json()
    if 'data' not in response:
        return None
    df = pd.DataFrame(response['data'])
    df.columns = ["timestamp", "open", "high", "low", "close", "volume"]
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit='ms')
    df = df.astype({"open": float, "high": float, "low": float, "close": float, "volume": float})
    return df


def apply_strategy(df):
    df['ema_fast'] = ta.trend.ema_indicator(df['close'], window=8).ema_indicator()
    df['ema_slow'] = ta.trend.ema_indicator(df['close'], window=21).ema_indicator()
    df['rsi'] = ta.momentum.rsi(df['close'], window=14)
    macd = ta.trend.macd(df['close'])
    df['macd_diff'] = macd.macd_diff()

    # 強化：多頭排列 + RSI 回升 + MACD 柱翻正 + 波動篩選
    latest = df.iloc[-1]
    prev = df.iloc[-2]

    conditions = [
        latest['ema_fast'] > latest['ema_slow'],               # EMA 多頭排列
        latest['rsi'] > 50 and latest['rsi'] > prev['rsi'],    # RSI 回升
        latest['macd_diff'] > 0 and prev['macd_diff'] <= 0,    # MACD 柱翻正
        (latest['high'] - latest['low']) > (latest['close'] * 0.01)  # 波動 > 1%
    ]
    return all(conditions)


def place_order(symbol, side):
    timestamp = get_server_time()
    url = f"{BASE_URL}/v1/user/market/order"
    params = {
        "symbol": symbol,
        "side": side,
        "positionSide": "LONG",
        "type": "MARKET",
        "quantity": str(TRADE_AMOUNT),
        "timestamp": timestamp
    }
    params['signature'] = sign(params)
    response = requests.post(url, headers=headers, data=params)
    print(f"下單結果 ({symbol}):", response.text)


def main():
    symbols = get_symbols()
    print(f"共取得 {len(symbols)} 個交易對")
    for symbol in symbols:
        try:
            df = get_klines(symbol)
            if df is not None and len(df) >= 30:
                if apply_strategy(df):
                    print(f"[✅ 訊號] {symbol} 符合條件，嘗試開多單")
                    place_order(symbol, "BUY")
                else:
                    print(f"[❌ 無訊號] {symbol} 略過")
            else:
                print(f"[⚠️ 資料不足] {symbol} 無法分析")
        except Exception as e:
            print(f"[錯誤] {symbol}: {e}")


if __name__ == "__main__":
    main()