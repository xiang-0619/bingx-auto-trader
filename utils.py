import requests
import time
import json
import hmac
import hashlib

with open("config.json") as f:
    config = json.load(f)

API_KEY = config["api_key"]
API_SECRET = config["api_secret"]
BASE_URL = "https://open-api.bingx.com"

def sign(params):
    query_string = '&'.join([f"{key}={params[key]}" for key in sorted(params)])
    signature = hmac.new(API_SECRET.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()
    return signature

def get_symbols():
    url = f"{BASE_URL}/openApi/swap/v2/quote/contracts"
    res = requests.get(url)
    data = res.json()
    if data["code"] == 0:
        return [item["symbol"] for item in data["data"] if "USDT" in item["symbol"]]
    return []

def get_balance():
    timestamp = int(time.time() * 1000)
    params = {
        "timestamp": timestamp,
        "recvWindow": 5000
    }
    params["signature"] = sign(params)
    headers = {"X-BX-APIKEY": API_KEY}
    res = requests.get(f"{BASE_URL}/openApi/swap/v2/user/balance", params=params, headers=headers)
    try:
        balances = res.json()["data"]["balance"]
        usdt_balance = next((item for item in balances if item["asset"] == "USDT"), None)
        if usdt_balance:
            return float(usdt_balance["availableBalance"])
    except:
        return 0
    return 0

def get_position(symbol):
    timestamp = int(time.time() * 1000)
    params = {
        "timestamp": timestamp,
        "recvWindow": 5000,
        "symbol": symbol
    }
    params["signature"] = sign(params)
    headers = {"X-BX-APIKEY": API_KEY}
    res = requests.get(f"{BASE_URL}/openApi/swap/v2/user/positions", params=params, headers=headers)
    try:
        return res.json()["data"]
    except:
        return []

def place_order(symbol, side, price, quantity):
    timestamp = int(time.time() * 1000)
    params = {
        "symbol": symbol,
        "side": side,
        "price": price,
        "quantity": quantity,
        "type": "MARKET",
        "timestamp": timestamp,
        "recvWindow": 5000
    }
    params["signature"] = sign(params)
    headers = {"X-BX-APIKEY": API_KEY}
    res = requests.post(f"{BASE_URL}/openApi/swap/v2/trade/order", params=params, headers=headers)
    return res.json()

def log_message(msg):
    print(f"[LOG] {time.strftime('%Y-%m-%d %H:%M:%S')} - {msg}")