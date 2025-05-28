import time
import hmac
import hashlib
import requests
import urllib.parse
from datetime import datetime

# 從 config.json 載入金鑰
import json
with open("config.json", "r") as f:
    config = json.load(f)

API_KEY = config["API_KEY"]
API_SECRET = config["API_SECRET"]

# 產生簽名
def generate_signature(params, secret):
    query_string = urllib.parse.urlencode(sorted(params.items()))
    signature = hmac.new(secret.encode(), query_string.encode(), hashlib.sha256).hexdigest()
    return signature

# 查詢 USDT 合約帳戶餘額（可用保證金）
def get_balance():
    try:
        url = "https://contract.bingx.com/api/v1/private/account/assets"
        timestamp = int(time.time() * 1000)

        params = {
            "timestamp": timestamp,
            "currency": "USDT"
        }

        signature = generate_signature(params, API_SECRET)
        params["signature"] = signature

        headers = {
            "X-BX-APIKEY": API_KEY
        }

        response = requests.get(url, headers=headers, params=params)
        if response.status_code != 200:
            print("❌ 錯誤：無法取得餘額，HTTP", response.status_code)
            print("回傳內容：", response.text)
            return 0.0

        data = response.json()
        balance = float(data["data"]["availableBalance"])
        return balance
    except Exception as e:
        print("❌ 發生例外錯誤：", str(e))
        return 0.0

# 輸出日誌
def log_message(msg):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{now}] {msg}")