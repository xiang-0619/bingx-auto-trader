import requests
import time
import numpy as np
import hmac
import hashlib
import os

BASE_URL = "https://open-api.bingx.com"
API_KEY = os.getenv("BINGX_API_KEY")
SECRET_KEY = os.getenv("BINGX_SECRET_KEY")
TRADE_SYMBOLS = ["BTC-USDT", "ETH-USDT", "XRP-USDT", "SOL-USDT", "DOGE-USDT"]
TRADE_AMOUNT = 5  # 每筆下單金額（USDT）

def sign(query_string, secret_key):
    return hmac.new(secret_key.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()

def get_klines(symbol):
    url = f"{BASE_URL}/openApi/swap/v2/quote/klines?symbol={symbol}&interval=30m&limit=100"
    response = requests.get(url).json()
    return response['data']

def calculate_indicators(prices):
    closes = np.array([float(c[4]) for c in prices])
    rsi = calculate_rsi(closes)
    macd_hist = calculate_macd(closes)
    ema_fast = closes[-5:].mean()
    ema_slow = closes[-20:].mean()
    return rsi[-1], macd_hist[-1], ema_fast, ema_slow

def calculate_rsi(prices, period=14):
    deltas = np.diff(prices)
    gain = np.maximum(deltas, 0)
    loss = np.maximum(-deltas, 0)
    avg_gain = np.convolve(gain, np.ones((period,))/period, mode='valid')
    avg_loss = np.convolve(loss, np.ones((period,))/period, mode='valid')
    rs = avg_gain / (avg_loss + 1e-6)
    return 100 - (100 / (1 + rs))

def calculate_macd(prices, short=12, long=26, signal=9):
    ema_short = ema(prices, short)
    ema_long = ema(prices, long)
    macd = ema_short - ema_long
    signal_line = ema(macd, signal)
    return macd - signal_line

def ema(data, window):
    weights = np.exp(np.linspace(-1., 0., window))
    weights /= weights.sum()
    return np.convolve(data, weights, mode='full')[:len(data)]

def place_order(symbol, side):
    timestamp = int(time.time() * 1000)
    endpoint = "/openApi/swap/v2/trade/order"
    url = BASE_URL + endpoint

    params = {
        "symbol": symbol,
        "side": side,
        "positionSide": "BOTH",
        "type": "MARKET",
        "quantity": str(TRADE_AMOUNT),
        "timestamp": timestamp
    }

    query_string = '&'.join([f"{key}={params[key]}" for key in sorted(params)])
    signature = sign(query_string, SECRET_KEY)
    headers = {"X-BX-APIKEY": API_KEY}
    final_url = url + "?" + query_string + f"&signature={signature}"
    response = requests.post(final_url, headers=headers)
    print(f"{symbol} {side} Order Response:", response.json())

def main():
    for symbol in TRADE_SYMBOLS:
        try:
            klines = get_klines(symbol)
            rsi, macd_hist, ema_fast, ema_slow = calculate_indicators(klines)

            print(f"{symbol} | RSI: {rsi:.2f}, MACD: {macd_hist:.4f}, EMA: {ema_fast:.2f} / {ema_slow:.2f}")

            if ema_fast > ema_slow and rsi < 70 and macd_hist > 0:
                place_order(symbol, "BUY")
            elif ema_fast < ema_slow and rsi > 30 and macd_hist < 0:
                place_order(symbol, "SELL")
        except Exception as e:
            print(f"Error with {symbol}: {e}")

if __name__ == "__main__":
    main()
