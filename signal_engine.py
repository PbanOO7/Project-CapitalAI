import yfinance as yf
import numpy as np

def compute_signal(symbol):
    df = yf.download(symbol, period="6mo", auto_adjust=True)
    if df.empty:
        return None

    df["EMA20"] = df["Close"].ewm(span=20).mean()
    df["EMA50"] = df["Close"].ewm(span=50).mean()
    df["ATR"] = (df["High"] - df["Low"]).rolling(14).mean()

    latest = df.iloc[-1]

    score = 0
    if latest["Close"] > latest["EMA20"]:
        score += 1
    if latest["EMA20"] > latest["EMA50"]:
        score += 1

    confidence = int((score / 2) * 100)

    entry = latest["Close"]
    stop = entry - latest["ATR"]

    return {
        "entry": float(entry),
        "stop": float(stop),
        "confidence": confidence
    }
