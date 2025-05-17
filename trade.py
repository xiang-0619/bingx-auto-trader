import requests
import time
import hmac
import hashlib
import numpy as np
import talib

API_KEY = "你的API_KEY"
API_SECRET = "你的API_SECRET"
BASE_URL = "https://open-api.bingx.com"

TRADE_AMOUNT = 10  # 單筆下單金額（USDT）

def get_server_time():
    return int(time.time() * 1000)

def sign_request(params):
    query_string = "&".join([f"{k}={v}" for k, v in sorted(params.items())])
    signature = hmac.new(API_SECRET.encode(), query_string.encode(), hashlib.sha256).hexdigest()
    return f"{query_string}&signature={signature}"

def get_symbols():
    url = f"{BASE_URL}/openApi/swap/v2/quote/contracts"
    return [s['symbol'] for s in requests.get(url).json()['data']]

def get_klines(symbol):
    url = f"{BASE_URL}/openApi/swap/v2/quote/klines?symbol={symbol}&interval=30m&limit=100"
    return requests.get(url).json()['data']

def calculate_indicators(prices):
    closes = np.array([float(c[4]) for c in prices])
    ema_fast = talib.EMA(closes, timeperiod=12)
    ema_slow = talib.EMA(closes, timeperiod=26)
    macd, macdsignal, _ = talib.MACD(closes, fastperiod=12, slowperiod=26, signalperiod=9)
    rsi = talib.RSI(closes, timeperiod=14)
    return ema_fast, ema_slow, macd, macdsignal, rsi

def should_buy(ema_fast, ema_slow, macd, macdsignal, rsi):
    return (
        ema_fast[-1] > ema_slow[-1] and
        macd[-1] > macdsignal[-1] and
        rsi[-1] < 70
    )

def should_sell(ema_fast, ema_slow, macd, macdsignal, rsi):
    return (
        ema_fast[-1] < ema_slow[-1] and
        macd[-1] < macdsignal[-1] and
        rsi[-1] > 30
    )

def place_order(symbol, side):
    path = "/openApi/swap/v2/trade/order"
    timestamp = get_server_time()
    params = {
        "symbol": symbol,
        "price": "0",  # 市價單
        "vol": str(TRADE_AMOUNT),
        "side": "1" if side == "BUY" else "2",
        "type": "1",
        "open_type": "1",
        "position_id": "0",
        "leverage": "10",
        "external_oid": str(timestamp),
        "stop_loss_price": "",
        "take_profit_price": "",
        "timestamp": str(timestamp),
        "apiKey": API_KEY,
    }
    signed_query = sign_request(params)
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    url = f"{BASE_URL}{path}?{signed_query}"
    res = requests.post(url, headers=headers)
    print(f"{symbol} {side} 訂單回應：", res.json())

def run():
    symbols = get_symbols()
    for symbol in symbols:
        try:
            prices = get_klines(symbol)
            if len(prices) < 30:
                continue
            ema_fast, ema_slow, macd, macdsignal, rsi = calculate_indicators(prices)
            if should_buy(ema_fast, ema_slow, macd, macdsignal, rsi):
                place_order(symbol, "BUY")
            elif should_sell(ema_fast, ema_slow, macd, macdsignal, rsi):
                place_order(symbol, "SELL")
        except Exception as e:
            print(f"{symbol} 發生錯誤：{e}")

if __name__ == "__main__":
    run()