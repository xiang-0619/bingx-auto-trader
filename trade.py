import time
import requests
import pandas as pd
from ta.trend import EMAIndicator, MACD
from ta.momentum import RSIIndicator
import os

API_KEY = os.getenv("BINGX_API_KEY")
API_SECRET = os.getenv("BINGX_SECRET_KEY")
BASE_URL = "https://api.bingx.com"  # 請確認官方合約API網址

TRADE_AMOUNT_USDT = 10  # 每筆交易金額

HEADERS = {
    "X-BX-APIKEY": API_KEY,
    # 可能還要簽名等，視官方API規定
}

def fetch_all_symbols():
    url = f"{BASE_URL}/api/v1/market/symbols"
    resp = requests.get(url)
    data = resp.json()
    if not data.get('success', True):
        print("取得幣種列表失敗:", data)
        return []
    # 只要永續合約 PERPETUAL (實際key依API文件調整)
    symbols = [item['symbol'] for item in data['data'] if item.get('contractType', '') == 'PERPETUAL']
    print(f"抓到 {len(symbols)} 個合約交易幣種")
    return symbols

def fetch_klines(symbol, interval='30m', limit=100):
    url = f"{BASE_URL}/api/v1/market/kline?symbol={symbol}&interval={interval}&limit={limit}"
    response = requests.get(url)
    data = response.json()
    if not data.get('success', True):
        print(f"{symbol} 取得K線失敗: {data}")
        return None
    klines = data['data']
    df = pd.DataFrame(klines, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['close'] = df['close'].astype(float)
    return df

def calculate_indicators(df):
    df['ema'] = EMAIndicator(df['close'], window=20).ema_indicator()
    df['rsi'] = RSIIndicator(df['close'], window=14).rsi()
    macd = MACD(df['close'])
    df['macd'] = macd.macd()
    df['macd_signal'] = macd.macd_signal()
    return df

def check_trade_signal(df):
    last = df.iloc[-1]
    prev = df.iloc[-2]

    bullish_trend = last['close'] > last['ema']
    bearish_trend = last['close'] < last['ema']

    rsi = last['rsi']
    rsi_buy = rsi < 30
    rsi_sell = rsi > 70

    macd_cross_up = prev['macd'] < prev['macd_signal'] and last['macd'] > last['macd_signal']
    macd_cross_down = prev['macd'] > prev['macd_signal'] and last['macd'] < last['macd_signal']

    if bullish_trend and macd_cross_up and rsi_buy:
        return "BUY"   # 多單進場

    if bearish_trend and macd_cross_down and rsi_sell:
        return "SELL"  # 空單進場

    return "HOLD"

def place_order(symbol, side, amount_usdt):
    # 合約下單範例，依BingX官方API調整
    # 這裡簡化示範，實際要計算手數、簽名、傳header等
    print(f"下單: {symbol} {side} {amount_usdt} USDT 合約")

    url = f"{BASE_URL}/api/v1/order"
    payload = {
        "symbol": symbol,
        "side": side,  # BUY或SELL
        "type": "MARKET",
        "quantity": amount_usdt,  # 這裡要轉成合約手數，需查合約價值換算
        "positionSide": "LONG" if side == "BUY" else "SHORT",  # 多單或空單
        # 其他必要參數...
    }
    # headers = {...}  # 含簽名和API KEY
    # response = requests.post(url, json=payload, headers=headers)
    # print(response.json())

def main():
    while True:
        symbols = fetch_all_symbols()
        for symbol in symbols:
            df = fetch_klines(symbol)
            if df is None or df.empty:
                continue
            df = calculate_indicators(df)
            signal = check_trade_signal(df)
            print(f"{symbol} 訊號: {signal}")
            if signal in ["BUY", "SELL"]:
                place_order(symbol, signal, TRADE_AMOUNT_USDT)
        print("等待30分鐘後繼續...")
        time.sleep(30 * 60)

if __name__ == "__main__":
    main()