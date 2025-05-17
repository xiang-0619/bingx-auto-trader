import time
import hmac
import hashlib
import requests
import numpy as np
import talib

# 設定你的 BingX API 金鑰
API_KEY = "你的API_KEY"
API_SECRET = "你的API_SECRET"
BASE_URL = "https://open-api.bingx.com"

TRADE_AMOUNT = 10  # 每筆下單金額（USDT）
INTERVAL = "1h"    # K線週期
TRADE_SYMBOLS = []  # 如果你要指定幣種，可在這裡列出，否則預設使用熱門幣種

# 取得時間戳記
def get_server_time():
    return int(time.time() * 1000)

# 建立簽名
def sign(query_string, secret):
    return hmac.new(secret.encode(), query_string.encode(), hashlib.sha256).hexdigest()

# 取得幣種清單
def get_symbols():
    url = f"{BASE_URL}/openApi/swap/v2/quote/contracts"
    res = requests.get(url).json()
    return [item['symbol'] for item in res['data']]

# 取得歷史K線
def get_klines(symbol):
    url = f"{BASE_URL}/openApi/swap/v2/quote/klines?symbol={symbol}&interval={INTERVAL}&limit=100"
    return requests.get(url).json()['data']

# 計算技術指標（EMA, RSI, MACD）
def calculate_indicators(prices):
    closes = np.array([float(c[4]) for c in prices])
    ema_fast = talib.EMA(closes, timeperiod=12)
    ema_slow = talib.EMA(closes, timeperiod=26)
    rsi = talib.RSI(closes, timeperiod=14)
    macd, macdsignal, _ = talib.MACD(closes, fastperiod=12, slowperiod=26, signalperiod=9)
    return ema_fast, ema_slow, rsi, macd, macdsignal

# 判斷是否為做多訊號
def should_open_long(ema_fast, ema_slow, rsi, macd, macdsignal):
    return (
        ema_fast[-1] > ema_slow[-1] and
        rsi[-1] > 50 and
        macd[-1] > macdsignal[-1]
    )

# 下單（做多）
def place_order(symbol, side):
    path = "/openApi/swap/v2/trade/order"
    timestamp = get_server_time()
    data = {
        "symbol": symbol,
        "side": side,
        "type": "MARKET",
        "positionSide": "LONG",
        "quantity": str(TRADE_AMOUNT),
        "timestamp": timestamp,
        "recvWindow": 5000,
    }
    query_string = '&'.join([f"{k}={v}" for k, v in sorted(data.items())])
    data["signature"] = sign(query_string, API_SECRET)
    headers = {"X-BX-APIKEY": API_KEY}
    response = requests.post(f"{BASE_URL}{path}", headers=headers, params=data)
    print(f"{symbol} 下單結果：", response.json())

# 主程式邏輯
def main():
    symbols = TRADE_SYMBOLS or get_symbols()
    for symbol in symbols:
        try:
            prices = get_klines(symbol)
            ema_fast, ema_slow, rsi, macd, macdsignal = calculate_indicators(prices)
            if should_open_long(ema_fast, ema_slow, rsi, macd, macdsignal):
                place_order(symbol, "BUY")
        except Exception as e:
            print(f"{symbol} 處理失敗：{e}")

# 每30分鐘運行一次（配合 GitHub Actions）
if __name__ == "__main__":
    main()