import time
import requests
import pandas as pd
from ta.trend import EMAIndicator, MACD
from ta.momentum import RSIIndicator
from config import API_KEY, SECRET_KEY, BASE_URL, TRADE_AMOUNT

INTERVAL = '15m'
LIMIT = 100
SYMBOLS = ['BTC-USDT', 'ETH-USDT', 'XRP-USDT']  # 可自行擴充

def get_klines(symbol):
    url = f"{BASE_URL}/v1/market/kline?symbol={symbol}&interval={INTERVAL}&limit={LIMIT}"
    try:
        response = requests.get(url)
        data = response.json()['data']
        df = pd.DataFrame(data)[['close', 'high', 'low', 'open', 'volume', 'timestamp']]
        df.columns = ['close', 'high', 'low', 'open', 'volume', 'timestamp']
        df = df.astype(float)
        return df
    except:
        return None

def signal_generator(df):
    close = df['close']
    open_ = df['open']

    ema_fast = EMAIndicator(close, window=9).ema_indicator()
    ema_slow = EMAIndicator(close, window=21).ema_indicator()
    macd = MACD(close).macd_diff()
    rsi = RSIIndicator(close, window=14).rsi()

    latest = -1
    previous = -2

    long_condition = (
        ema_fast[latest] > ema_slow[latest] and
        macd[previous] < 0 and macd[latest] > 0 and
        rsi[previous] < 50 and rsi[latest] > 50
    )

    short_condition = (
        ema_fast[latest] < ema_slow[latest] and
        macd[previous] > 0 and macd[latest] < 0 and
        rsi[previous] > 50 and rsi[latest] < 50
    )

    if long_condition:
        return 'long'
    elif short_condition:
        return 'short'
    else:
        return None

def place_order(symbol, side):
    url = f"{BASE_URL}/v1/user/trade/contract/order"
    headers = {"X-BX-APIKEY": API_KEY}
    data = {
        "symbol": symbol,
        "price": "0",
        "vol": TRADE_AMOUNT,
        "side": 1 if side == "long" else 2,
        "type": 1,
        "open_type": "isolated",
        "position_id": 0,
        "leverage": 20,
        "external_oid": str(int(time.time() * 1000)),
        "stop_loss_price": "",
        "take_profit_price": "",
        "position_mode": "double_hold"
    }

    # ⚠️ TODO: 加入簽名等認證邏輯（若使用 BingX API）
    try:
        response = requests.post(url, json=data, headers=headers)
        print(f"[{symbol}] {side.upper()} order placed: {response.text}")
    except Exception as e:
        print(f"[{symbol}] Order failed: {e}")

def main():
    for symbol in SYMBOLS:
        df = get_klines(symbol)
        if df is None or df.empty:
            print(f"[{symbol}] K線資料獲取失敗")
            continue

        signal = signal_generator(df)
        if signal:
            place_order(symbol, signal)
        else:
            print(f"[{symbol}] 無明確訊號")

if __name__ == "__main__":
    main()