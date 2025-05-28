import requests
import json
from datetime import datetime  # ← 加這行

def load_config():
    with open("config.json", "r") as f:
        return json.load(f)

def get_balance(api_key, api_secret):
    url = "https://contract.bingx.com/api/v1/private/account/assets"
    params = {
        "timestamp": int(datetime.now().timestamp() * 1000),
        "currency": "USDT",
    }
    headers = {
        "X-BX-APIKEY": api_key
    }

    # 加簽名（略，這裡假設你有簽名函式）
    signature = sign(api_secret, params)
    params["signature"] = signature

    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        return float(data["data"]["availableBalance"])
    except Exception as e:
        log_message(f"取得餘額失敗: {e}")
        return 0.0

def log_message(message):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{now}] {message}")