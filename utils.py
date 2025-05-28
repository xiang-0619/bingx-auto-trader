import requests
import time
import hmac
import hashlib

BASE_URL = "https://contract.bingx.com"  # 正確的永續合約 API 主機

def get_timestamp():
    return int(time.time() * 1000)

def sign(params, secret):
    query_string = '&'.join([f"{k}={params[k]}" for k in sorted(params)])
    return hmac.new(secret.encode(), query_string.encode(), hashlib.sha256).hexdigest()

def get_balance(api_key, api_secret):
    url = BASE_URL + "/api/v1/private/account/assets"
    params = {
        "timestamp": get_timestamp(),
        "currency": "USDT"
    }
    signature = sign(params, api_secret)
    params["signature"] = signature
    headers = {
        "X-API-KEY": api_key
    }
    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        # 根據 BingX 永續合約的 API 回傳結構做調整，這裡假設 data['data']['availableBalance']
        return float(data['data']['availableBalance'])
    except requests.exceptions.RequestException as e:
        print(f"取得餘額失敗: {e}")
        return 0.0
        from datetime import datetime

def log_message(message):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{now}] {message}")