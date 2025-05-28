import json
import time
import requests
import hmac
import hashlib
from utils import get_symbols, log_message, strategy_should_open_long
from datetime import datetime

# 讀取 API KEY 與 SECRET
with open("config.json", "r") as f:
    config = json.load(f)

API_KEY = config["API_KEY"]
API_SECRET = config["API_SECRET"]

BASE_URL = "https://contract.bingx.com"

# 下單參數
ORDER_AMOUNT = 10  # 每單 USDT 金額
LEVERAGE = 20
INTERVAL = 15 * 60  # 每 15 分鐘執行一次

def sign(params):
    query = "&".join([f"{key}={params[key]}" for key in sorted(params)])
    signature = hmac.new(API_SECRET.encode(), query.encode(), hashlib.sha256).hexdigest()
    return signature

def get_available_balance():
    timestamp = str(int(time.time() * 1000))
    params = {
        "timestamp": timestamp,
        "currency": "USDT"
    }
    params["signature"] = sign(params)
    headers = {"X-BX-APIKEY": API_KEY}
    try:
        response = requests.get(f"{BASE_URL}/api/v1/private/account/assets", params=params, headers=headers)
        response.raise_for_status()
        data = response.json()
        return float(data["data"]["availableBalance"])
    except Exception as e:
        log_message(f"❌ 取得餘額失敗: {e}")
        return 0.0

def place_order(symbol):
    timestamp = str(int(time.time() * 1000))
    params = {
        "symbol": symbol,
        "side": "BUY",
        "positionSide": "LONG",
        "type": "MARKET",
        "quantity": str(ORDER_AMOUNT),
        "leverage": str(LEVERAGE),
        "timestamp": timestamp,
    }
    params["signature"] = sign(params)
    headers = {"X-BX-APIKEY": API_KEY}
    try:
        response = requests.post(f"{BASE_URL}/api/v1/user/market/order", params=params, headers=headers)
        data = response.json()
        log_message(f"✅ 開多單成功: {symbol} -> {data}")
    except Exception as e:
        log_message(f"❌ 開單失敗: {symbol} -> {e}")

def main():
    log_message(f"🚀 交易腳本啟動：目標每單 {ORDER_AMOUNT} USDT，槓桿 {LEVERAGE} 倍")
    balance = get_available_balance()
    log_message(f"💰 可用保證金：{balance} USDT")
    if balance < ORDER_AMOUNT:
        log_message("❌ 資金不足，不開單")
        return

    symbols = get_symbols()
    for symbol in symbols:
        try:
            if strategy_should_open_long(symbol):
                place_order(symbol)
                time.sleep(1)  # 避免過快觸發 API 限制
        except Exception as e:
            log_message(f"⚠️ 檢查 {symbol} 發生錯誤: {e}")

if __name__ == "__main__":
    main()