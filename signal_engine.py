import pandas as pd
import yfinance as yf

from chart_brain import chart_probability
from market_intelligence import get_news_sentiment
from fundamental_engine import fundamental_score


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
    try:
        df = yf.download(
            symbol,
            period=period,
            auto_adjust=True,
            progress=False,
            threads=False,
        )
    except Exception:
        return pd.DataFrame()

    # RELAXED FILTER (previously 220)
    if df is None or df.empty or len(df) < 80:
        return pd.DataFrame()

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df.columns = [str(c).strip().lower() for c in df.columns]

    required = {"open", "close", "high", "low", "volume"}
    if not required.issubset(df.columns):
        return pd.DataFrame()

    # EMAs
    df["ema20"] = df["close"].ewm(span=20, adjust=False).mean()
    df["ema50"] = df["close"].ewm(span=50, adjust=False).mean()
    df["ema200"] = df["close"].ewm(span=200, adjust=False).mean()

    # ATR
    high_low = df["high"] - df["low"]
    high_close = (df["high"] - df["close"].shift()).abs()
    low_close = (df["low"] - df["close"].shift()).abs()

    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df["atr"] = tr.rolling(14).mean()

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

    symbol = symbol.strip().upper()

    df = _prepare_df(symbol)

    if df.empty:
        return None

    latest = df.iloc[-1]

    close = float(latest["close"])
    ema20 = float(latest["ema20"])
    ema50 = float(latest["ema50"])
    ema200 = float(latest["ema200"])
    atr = float(latest["atr"])

    if atr <= 0:
        return None

    technical_score = 0

    # Market regime
    if _market_regime_ok():
        technical_score += 10

    # RELAXED TREND RULE
    if close > ema20:
        technical_score += 10

    if ema20 > ema50:
        technical_score += 10

    if close > ema50:
        technical_score += 5

    # AI / external scoring engines
    chart_score = chart_probability(df)
    sentiment_score = get_news_sentiment(symbol)
    fund_score = fundamental_score(symbol)

    confidence = technical_score + chart_score + sentiment_score + fund_score
    confidence = max(0, min(int(confidence), 90))

    # RELAXED CONFIDENCE FILTER
    if confidence < 25:
        return None

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
    }


def scan_universe() -> pd.DataFrame:

    signals = []

    for symbol in UNIVERSE:

        signal = compute_signal(symbol)

        if signal:
            signals.append(signal)

    if not signals:
        return pd.DataFrame()

    return (
        pd.DataFrame(signals)
        .sort_values(["confidence", "entry"], ascending=[False, False])
        .reset_index(drop=True)
    )