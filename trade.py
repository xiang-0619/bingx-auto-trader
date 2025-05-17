import requests
import hmac
import hashlib
import time
import os
from datetime import datetime
import numpy as np

API_KEY = os.getenv("BINGX_API_KEY")
API_SECRET = os.getenv("BINGX_API_SECRET")
BASE_URL = "https://open-api.bingx.com"

TRADE_AMOUNT = 15  # 每筆 15 USDT

def get_symbols():
    url = f"{BASE_URL}/openApi/swap/v2/quote/contracts"
    res = requests.get(url).json()
    return [s['symbol'] for s in res['data'] if s['quoteAsset'] == 'USDT']

def get_klines(symbol):
    url = f"{BASE_URL}/openApi/swap/v2/quote/klines?symbol={symbol}&interval=1h&limit=100"
    return requests.get(url).json()['data']

def calculate_indicators(prices):
    closes = np.array([float(c[4]) for c in prices])
    rsi = calc_rsi(closes)
    bb_lower = calc_bollinger_bands(closes)
    return rsi[-1], bb_lower[-1]

def calc_rsi(closes, period=14):
    delta = np.diff(closes)
    gain = np.where(delta > 0, delta, 0)
    loss = np.where(delta < 0, -delta, 0)
    avg_gain = np.convolve(gain, np.ones(period)/period, 'valid')
    avg_loss = np.convolve(loss, np.ones(period)/period, 'valid')
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return np.concatenate((np.full(period-1, np.nan), rsi))

def calc_bollinger_bands(closes, period=20):
    ma = np.convolve(closes, np.ones(period)/period, 'valid')
    std = np.array([np.std(closes[i-period+1:i+1]) for i in range(period-1, len(closes))])
    lower_band = ma - 2 * std
    return np.concatenate((np.full(period-1, np.nan), lower_band))

def sign(params):
    query = '&'.join(f"{k}={v}" for k, v in sorted(params.items()))
    return hmac.new(API_SECRET.encode(), query.encode(), hashlib.sha256).hexdigest()

def place_order(symbol):
    url = f"{BASE_URL}/openApi/swap/v2/trade/order"
    params = {
        "symbol": symbol,
        "side": "BUY",
        "positionSide": "LONG",
        "type": "MARKET",
        "quantity": TRADE_AMOUNT,
        "timestamp": int(time.time() * 1000),
    }
    params["signature"] = sign(params)
    headers = {"X-BX-APIKEY": API_KEY}
    res = requests.post(url, headers=headers, params=params).json()
    print(f"[{datetime.now()}] 下單：{symbol} - {res}")

def main():
    symbols = get_symbols()
    for symbol in symbols:
        try:
            klines = get_klines(symbol)
            rsi, bb = calculate_indicators(klines)
            current_price = float(klines[-1][4])
            if rsi < 30 and current_price < bb:
                place_order(symbol)
        except Exception as e:
            print(f"錯誤於 {symbol}：{e}")

if __name__ == "__main__":
    main()
