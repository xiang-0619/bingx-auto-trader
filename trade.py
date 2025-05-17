import requests
import time
import hmac
import hashlib
import numpy as np
import ta
import os
import time
import requests
import numpy as np
import ta  # 使用純 Python TA 套件
from datetime import datetime

BASE_URL = "https://open-api.bingx.com"
API_KEY = os.getenv("BINGX_API_KEY")
SECRET_KEY = os.getenv("BINGX_SECRET_KEY")
TRADE_AMOUNT = 10  # 單筆下單金額（USDT）

def get_server_time():
    return int(time.time() * 1000)

def sign(params):
    query_string = '&'.join([f"{k}={v}" for k, v in sorted(params.items())])
    signature = hmac.new(SECRET_KEY.encode(), query_string.encode(), hashlib.sha256).hexdigest()
    return signature

def get_symbols():
    url = f"{BASE_URL}/openApi/swap/v2/quote/contracts"
    return [s['symbol'] for s in requests.get(url).json()['data']]

def get_klines(symbol):
    url = f"{BASE_URL}/openApi/swap/v2/quote/klines?symbol={symbol}&interval=15m&limit=100"
    return requests.get(url).json()['data']

def calculate_signals(prices):
    df = np.array(prices, dtype=float)
    close = df[:, 4]
    if len(close) < 50:
        return False

    rsi = ta.momentum.RSIIndicator(close).rsi().values[-1]
    macd_diff = ta.trend.MACD(close).macd_diff().values[-1]
    ema_fast = ta.trend.EMAIndicator(close, window=9).ema_indicator().values[-1]
    ema_slow = ta.trend.EMAIndicator(close, window=21).ema_indicator().values[-1]

    uptrend = ema_fast > ema_slow
    buy_signal = uptrend and rsi < 30 and macd_diff > 0
    return buy_signal

def place_order(symbol):
    timestamp = get_server_time()
    params = {
        "symbol": symbol,
        "side": "BUY",
        "positionSide": "LONG",
        "type": "MARKET",
        "quantity": TRADE_AMOUNT,
        "timestamp": timestamp,
        "recvWindow": 5000
    }
    params["signature"] = sign(params)
    headers = {"X-BX-APIKEY": API_KEY}
    url = f"{BASE_URL}/openApi/swap/v2/trade/order"
    res = requests.post(url, headers=headers, data=params)
    print(f"Order placed for {symbol}: {res.text}")

def main():
    for symbol in get_symbols():
        try:
            klines = get_klines(symbol)
            if calculate_signals(klines):
                place_order(symbol)
        except Exception as e:
            print(f"Error with {symbol}: {e}")

if __name__ == "__main__":
    main()