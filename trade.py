import requests
import time
import json
import hmac
import hashlib
import ta
import pandas as pd
from datetime import datetime

with open('config.json') as f:
    config = json.load(f)

API_KEY = config['api_key']
API_SECRET = config['api_secret']
BASE_URL = 'https://api.bingx.com'

HEADERS = {
    'Content-Type': 'application/json',
    'X-BX-APIKEY': API_KEY
}

SYMBOLS_URL = 'https://api.bingx.com/api/v1/market/getAllContracts'

def sign(params, secret):
    query_string = '&'.join([f"{k}={v}" for k, v in sorted(params.items())])
    return hmac.new(secret.encode(), query_string.encode(), hashlib.sha256).hexdigest()

def get_symbols():
    try:
        response = requests.get(SYMBOLS_URL)
        symbols = response.json()['data']
        return [s['symbol'] for s in symbols if s['contractType'] == 'linear_perpetual']
    except Exception as e:
        print("Failed to get symbols:", e)
        return []

def get_klines(symbol, interval='15m', limit=100):
    url = f"{BASE_URL}/v1/market/kline"
    params = {
        "symbol": symbol,
        "interval": interval,
        "limit": limit
    }
    try:
        res = requests.get(url, params=params).json()
        df = pd.DataFrame(res['data'])
        df.columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        df['close'] = pd.to_numeric(df['close'])
        df['open'] = pd.to_numeric(df['open'])
        df['high'] = pd.to_numeric(df['high'])
        df['low'] = pd.to_numeric(df['low'])
        return df
    except Exception as e:
        print(f"[{symbol}] Failed to get kline:", e)
        return None

def analyze(df):
    df['ema_fast'] = ta.trend.ema_indicator(df['close'], window=9).ema_indicator()
    df['ema_slow'] = ta.trend.ema_indicator(df['close'], window=21).ema_indicator()
    df['macd'] = ta.trend.macd_diff(df['close'])
    df['rsi'] = ta.momentum.RSIIndicator(df['close']).rsi()
    last = df.iloc[-1]
    prev = df.iloc[-2]
    
    signal_macd = prev['macd'] < 0 and last['macd'] > 0
    signal_rsi = prev['rsi'] < 30 and last['rsi'] > 30
    trend_ok = last['ema_fast'] >= last['ema_slow']
    return signal_macd and signal_rsi and trend_ok

def place_order(symbol, side, amount):
    url = f"{BASE_URL}/v1/user/market/order"
    params = {
        "symbol": symbol,
        "side": side,
        "type": "MARKET",
        "positionSide": "LONG" if side == "BUY" else "SHORT",
        "quantity": amount,
        "timestamp": int(time.time() * 1000)
    }
    params['signature'] = sign(params, API_SECRET)
    try:
        res = requests.post(url, headers=HEADERS, data=json.dumps(params)).json()
        print(f"[{symbol}] Order Result:", res)
        return res
    except Exception as e:
        print(f"[{symbol}] Order Error:", e)

def get_usdt_balance():
    url = f"{BASE_URL}/v1/user/accounts"
    params = {
        "timestamp": int(time.time() * 1000)
    }
    params['signature'] = sign(params, API_SECRET)
    res = requests.get(url, headers=HEADERS, params=params).json()
    for acc in res.get('data', []):
        if acc['asset'] == 'USDT':
            return float(acc['availableBalance'])
    return 0

def main():
    usdt = get_usdt_balance()
    if usdt < 10:
        print("資金不足，不開單")
        return

    symbols = get_symbols()
    opened = []
    for symbol in symbols:
        df = get_klines(symbol)
        if df is None or len(df) < 30:
            continue
        try:
            if analyze(df):
                order_amount = round((usdt * 0.1) / df.iloc[-1]['close'], 3)
                print(f"[{symbol}] ✅ 符合條件，準備開單")
                place_order(symbol, "BUY", order_amount)
                opened.append(symbol)
            else:
                print(f"[{symbol}] ❌ 條件不符，跳過")
        except Exception as e:
            print(f"[{symbol}] Error in analysis:", e)

    print(f"✅ 共開單：{opened}")

if __name__ == "__main__":
    main()