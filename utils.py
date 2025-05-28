import requests
from datetime import datetime
import logging

def log_message(message):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{now}] {message}")
    logging.info(message)

def get_symbols():
    url = "https://open-api.bingx.com/openApi/swap/v2/quote/contracts"
    try:
        response = requests.get(url)
        data = response.json()
        return [item["symbol"] for item in data["data"] if item["status"] == "TRADING"]
    except Exception as e:
        log_message(f"⚠️ 無法獲取幣種列表: {e}")
        return []

def strategy_should_open_long(symbol):
    # ✅ 這是一個簡單範例策略，建議你換成自己的策略邏輯
    # 為了示範方便，這裡隨機開倉（不建議實際使用）
    import random
    return random.random() < 0.03  # 大約 3% 機率開單