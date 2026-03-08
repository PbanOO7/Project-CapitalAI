import pandas as pd
import yfinance as yf


UNIVERSE = [
    "RELIANCE.NS",
    "TCS.NS",
    "INFY.NS",
    "HDFCBANK.NS",
    "ICICIBANK.NS",
    "SBIN.NS",
    "TATAMOTORS.NS",
    "NTPC.NS",
    "LT.NS",
]


def _prepare_df(symbol: str, period: str = "9mo") -> pd.DataFrame:
    df = yf.download(symbol, period=period, auto_adjust=True, progress=False)

    if df is None or df.empty or len(df) < 220:
        return pd.DataFrame()

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df.columns = [str(c).strip().lower() for c in df.columns]

    required = {"close", "high", "low", "volume"}
    if not required.issubset(df.columns):
        return pd.DataFrame()

    df["ema20"] = df["close"].ewm(span=20, adjust=False).mean()
    df["ema50"] = df["close"].ewm(span=50, adjust=False).mean()
    df["ema200"] = df["close"].ewm(span=200, adjust=False).mean()

    high_low = df["high"] - df["low"]
    high_close = (df["high"] - df["close"].shift()).abs()
    low_close = (df["low"] - df["close"].shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df["atr"] = tr.rolling(14).mean()

    df["vol20"] = df["volume"].rolling(20).mean()
    df["high20_prev"] = df["high"].rolling(20).max().shift(1)

    return df.dropna()


def _market_regime_ok() -> bool:
    df = _prepare_df("^NSEI", period="12mo")
    if df.empty:
        return False
    latest = df.iloc[-1]
    return float(latest["close"]) > float(latest["ema200"])


def compute_signal(symbol: str) -> dict | None:
    if not symbol:
        return None

    df = _prepare_df(symbol)
    if df.empty:
        return None

    latest = df.iloc[-1]

    close = float(latest["close"])
    ema20 = float(latest["ema20"])
    ema50 = float(latest["ema50"])
    ema200 = float(latest["ema200"])
    atr = float(latest["atr"])
    volume = float(latest["volume"])
    vol20 = float(latest["vol20"])
    high20_prev = float(latest["high20_prev"])

    if atr <= 0:
        return None

    score = 0

    regime_ok = _market_regime_ok()
    if regime_ok:
        score += 20

    if close > ema20 > ema50 > ema200:
        score += 30

    if close > high20_prev:
        score += 20

    if (atr / close) < 0.05:
        score += 10

    if volume > 1.2 * vol20:
        score += 10

    # simple momentum candle check
    prev = df.iloc[-2]
    if float(prev["close"]) < float(prev["open"]) and close > float(prev["high"]):
        score += 10

    confidence = int(min(score, 90))

    stop = min(close - atr, float(df["low"].rolling(10).min().iloc[-1]))
    if stop >= close:
        stop = close - atr

    risk_per_share = close - stop
    if risk_per_share <= 0:
        return None

    target = close + 2 * risk_per_share

    return {
        "symbol": symbol,
        "entry": round(close, 2),
        "stop": round(stop, 2),
        "target": round(target, 2),
        "confidence": confidence,
        "risk_per_share": round(risk_per_share, 2),
        "regime_ok": regime_ok,
    }


def scan_universe() -> pd.DataFrame:
    signals = []
    for symbol in UNIVERSE:
        signal = compute_signal(symbol)
        if signal:
            signals.append(signal)

    if not signals:
        return pd.DataFrame()

    df = pd.DataFrame(signals)
    return df.sort_values(["confidence", "entry"], ascending=[False, False]).reset_index(drop=True)