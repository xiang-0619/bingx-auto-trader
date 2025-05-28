import json
import requests
import time
from datetime import datetime
from strategy import should_open_position
from utils import get_symbols, get_balance, get_position, place_order, log_message

# 讀取設定檔
with open("config.json") as f:
    config = json.load(f)

API_KEY = config["api_key"]
API_SECRET = config["api_secret"]
TRADE_AMOUNT = float(config.get("trade_amount", 10))
LEVERAGE = int(config.get("leverage", 20))
BASE_URL = "https://api-swap.bingx.com"

print(f"🚀 交易腳本啟動：目標每單 {TRADE_AMOUNT} USDT，槓桿 {LEVERAGE} 倍")

# 取得目前可用 USDT 餘額
usdt_balance = get_balance(API_KEY, API_SECRET)
print(f"💰 當前可用 USDT 餘額：{usdt_balance:.2f} USDT")

# 計算每單實際所需保證金（含緩衝）
required_margin = TRADE_AMOUNT / LEVERAGE + 0.5
print(f"📊 每單所需保證金（含緩衝）：{required_margin:.2f} USDT")

if usdt_balance < required_margin:
    print("⚠️ 可用資金不足，跳過所有下單")
    exit()

# 獲取可交易幣種
symbols = get_symbols()

for symbol in symbols:
    try:
        # 判斷目前是否已持倉，避免重複下單
        current_position = get_position(API_KEY, API_SECRET, symbol)
        if current_position:
            print(f"📌 {symbol} 已持倉，跳過")
            continue

        # 判斷策略是否符合進場條件
        decision = should_open_position(symbol)
        if not decision["should_open"]:
            continue

        side = decision["side"]  # "BUY" or "SELL"

        print(f"✅ 訊號成立：{symbol} - {side}，準備下單...")

        order_result = place_order(API_KEY, API_SECRET, symbol, side, TRADE_AMOUNT, LEVERAGE)

        if order_result["success"]:
            print(f"🎯 成功開單：{symbol} - {side} - 金額 {TRADE_AMOUNT} USDT")
            log_message(f"✅ {symbol} - {side} 已開單")
        else:
            print(f"❌ 開單失敗：{symbol} - 原因：{order_result.get('message', '未知錯誤')}")
    
    except Exception as e:
        print(f"❗️ 發生錯誤：{symbol} - {str(e)}")