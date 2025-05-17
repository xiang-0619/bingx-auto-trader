import os
import time
import hmac
import hashlib
import requests
import numpy as np
import talib

API_KEY = os.getenv("BINGX_API_KEY")
SECRET_KEY = os.getenv("BINGX_SECRET_KEY")
BASE_URL = "https://open-api.bingx.com"
TRADE_AMOUNT = 10

def get_server_time():
    return int(time.time() * 1000)

def sign(params):
    query_string = '&'.join([f"{k}={v}" for k, v in sorted(params.items())])
    return hmac.new(SECRET_KEY.encode(), query_string.encode(), hashlib.sha256).hexdigest()

def get_symbols():
    url = f"{BASE_URL}/openApi/swap/v2/quote/contracts"
    response = requests.get(url).json()
    return [s['symbol'] for s in response['data']]

def get_klines(symbol):
    url = f"{BASE_URL}/openApi/swap/v2/quote/klines?symbol={symbol}&interval=15m&limit=100"
    response = requests.get(url).json()
    return response['data'] if 'data' in response else []

def calculate_indicators(klines):
    closes = np.array([float(k[4]) for k in klines])
    highs = np.array([float(k[2]) for k in klines])
    lows = np.array([float(k[3]) for k in klines])

    macd, macdsignal, _ = talib.MACD(closes, fastperiod=12, slowperiod=26, signalperiod=9)
    rsi = talib.RSI(closes, timeperiod=14)
    ema12 = talib.EMA(closes, timeperiod=12)
    ema26 = talib.EMA(closes, timeperiod=26)
    atr = talib.ATR(highs, lows, closes, timeperiod=14)

    return {
        "macd": macd,
        "macdsignal": macdsignal,
        "rsi": rsi,
        "ema12": ema12,
        "ema26": ema26,
        "atr": atr
    }

def place_order(symbol, side):
    url = f"{BASE_URL}/openApi/swap/v2/trade/order"
    timestamp = get_server_time()
    data = {
        "symbol": symbol,
        "price": "0",
        "vol": TRADE_AMOUNT,
        "side": side,
        "type": 1,
        "openType": "isolated",
        "positionId": 0,
        "leverage": 20,
        "externalOid": str(timestamp),
        "timestamp": timestamp,
        "recvWindow": 5000
    }
    data["signature"] = sign(data)
    headers = {"X-BX-APIKEY": API_KEY}
    response = requests.post(url, headers=headers, data=data)
    print(f"Order response for {symbol} ({side}):", response.json())

def should_long(ind):
    if len(ind['macd']) < 2 or len(ind['rsi']) < 2 or len(ind['ema12']) < 1:
        return False
    return (
        ind['macd'][-2] < 0 and ind['macd'][-1] > 0 and
        ind['rsi'][-2] < ind['rsi'][-1] and ind['rsi'][-1] > 50 and
        ind['ema12'][-1] > ind['ema26'][-1] and
        ind['atr'][-1] > np.mean(ind['atr'][-10:])
    )

def main():
    symbols = get_symbols()
    for symbol in symbols:
        try:
            klines = get_klines(symbol)
            if not klines or len(klines) < 50:
                continue
            indicators = calculate_indicators(klines)
            if should_long(indicators):
                place_order(symbol, "1")
        except Exception as e:
            print(f"Error processing {symbol}: {e}")

if __name__ == "__main__":
    main()