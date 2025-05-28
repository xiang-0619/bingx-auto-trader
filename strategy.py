import requests
import pandas as pd
import ta

def get_klines(symbol, interval="15m", limit=100):
    url = f"https://open-api.bingx.com/openApi/swap/v2/quote/klines?symbol={symbol}&interval={interval}&limit={limit}"
    res = requests.get(url)
    data = res.json()
    if not data.get("data"):
        return None
    df = pd.DataFrame(data["data"], columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["close"] = pd.to_numeric(df["close"])
    return df

def should_open_position(symbol):
    df = get_klines(symbol)
    if df is None or len(df) < 35:
        return {"should_open": False}

    # 計算技術指標
    df["ema_12"] = ta.trend.ema_indicator(df["close"], window=12).fillna(0)
    df["ema_26"] = ta.trend.ema_indicator(df["close"], window=26).fillna(0)
    df["macd"] = df["ema_12"] - df["ema_26"]
    df["rsi"] = ta.momentum.rsi(df["close"], window=14).fillna(0)

    latest = df.iloc[-1]
    previous = df.iloc[-2]

    # 多單進場條件（激進型）
    if (
        latest["ema_12"] > latest["ema_26"] and
        latest["macd"] > 0 and previous["macd"] <= 0 and
        latest["rsi"] > 50 and previous["rsi"] < latest["rsi"]
    ):
        return {"should_open": True, "side": "BUY"}

    # 空單進場條件（激進型）
    if (
        latest["ema_12"] < latest["ema_26"] and
        latest["macd"] < 0 and previous["macd"] >= 0 and
        latest["rsi"] < 50 and previous["rsi"] > latest["rsi"]
    ):
        return {"should_open": True, "side": "SELL"}

    return {"should_open": False}