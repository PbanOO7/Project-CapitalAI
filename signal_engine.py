import yfinance as yf
import pandas as pd


def compute_signal(symbol: str):
    if not symbol:
        return None

    try:
        df = yf.download(symbol, period="6mo", auto_adjust=True, progress=False)
    except Exception:
        return None

    if df is None or df.empty or len(df) < 60:
        return None

    # Flatten MultiIndex columns if present
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    # Normalize names
    df.columns = [str(c).strip().lower() for c in df.columns]

    required = {"close", "high", "low"}
    if not required.issubset(df.columns):
        return None

    # Indicators
    df["ema20"] = df["close"].ewm(span=20, adjust=False).mean()
    df["ema50"] = df["close"].ewm(span=50, adjust=False).mean()
    df["atr"] = (df["high"] - df["low"]).rolling(14).mean()

    latest = df.iloc[-1]

    close = float(latest["close"])
    ema20 = float(latest["ema20"])
    ema50 = float(latest["ema50"])
    atr = float(latest["atr"]) if pd.notna(latest["atr"]) else 0.0

    if atr <= 0:
        return None

    score = 0
    if close > ema20:
        score += 1
    if ema20 > ema50:
        score += 1

    confidence = int((score / 2) * 100)
    entry = close
    stop = entry - atr

    return {
        "entry": round(entry, 2),
        "stop": round(stop, 2),
        "confidence": confidence
    }