import requests
import time
import hmac
import hashlib

BASE_URL = "https://api-swap.bingx.com"

def get_timestamp():
    return str(int(time.time() * 1000))

def sign_request(secret_key, params):
    query_string = '&'.join([f"{key}={params[key]}" for key in sorted(params)])
    return hmac.new(secret_key.encode(), query_string.encode(), hashlib.sha256).hexdigest()

def get_balance(api_key, api_secret):
    endpoint = "/swap-api/v1/user/balance"
    url = BASE_URL + endpoint

    params = {
        "timestamp": get_timestamp()
    }
    signature = sign_request(api_secret, params)
    headers = {
        "X-BX-APIKEY": api_key
    }

    params["signature"] = signature
    response = requests.get(url, headers=headers, params=params)
    data = response.json()

    if data.get("code") != 0:
        print("❌ 取得資金失敗：", data)
        return 0

    usdt_balance = 0
    for asset in data["data"]:
        if asset["asset"] == "USDT":
            usdt_balance = float(asset["availableMargin"])
            break

    return usdt_balance

def log_message(msg):
    print(f"📋 LOG：{msg}")