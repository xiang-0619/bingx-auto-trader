import json
from strategy import should_open_position
from utils import get_balance, log_message

# 載入 API 金鑰
with open("config.json") as f:
    config = json.load(f)

API_KEY = config['api_key']
API_SECRET = config['api_secret']

# 每單下單 10 USDT，槓桿 20 倍
order_amount = 10
leverage = 20

print(f"🚀 交易腳本啟動：目標每單 {order_amount} USDT，槓桿 {leverage} 倍")

# 查詢餘額
usdt_balance = get_balance(API_KEY, API_SECRET)
print(f"💰 可用保證金：{usdt_balance} USDT")

if usdt_balance < order_amount:
    log_message("❌ 資金不足，不開單")
else:
    # 簡單示範：判斷是否有交易機會
    symbols = ["BTC-USDT", "ETH-USDT", "SOL-USDT"]
    for symbol in symbols:
        signal = should_open_position(symbol)
        if signal:
            log_message(f"✅ 準備開單：{symbol}（理由：{signal}）")
            # place_order() 可加上開單邏輯