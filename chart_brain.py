import pandas as pd


def detect_trend(df: pd.DataFrame) -> str:
    highs = df["high"].tail(5).reset_index(drop=True)
    lows = df["low"].tail(5).reset_index(drop=True)

    if highs.is_monotonic_increasing and lows.is_monotonic_increasing:
        return "UPTREND"
    if highs.is_monotonic_decreasing and lows.is_monotonic_decreasing:
        return "DOWNTREND"
    return "RANGE"


def detect_breakout(df: pd.DataFrame) -> bool:
    if len(df) < 21:
        return False
    last_close = float(df["close"].iloc[-1])
    prev_high = float(df["high"].rolling(20).max().shift(1).iloc[-1])
    return last_close > prev_high


def detect_pullback(df: pd.DataFrame) -> bool:
    if "ema20" not in df.columns:
        return False
    last_low = float(df["low"].iloc[-1])
    ema20 = float(df["ema20"].iloc[-1])
    return last_low <= ema20


def detect_bullish_engulfing(df: pd.DataFrame) -> bool:
    if len(df) < 2:
        return False

    prev = df.iloc[-2]
    curr = df.iloc[-1]

    return (
        float(prev["close"]) < float(prev["open"])
        and float(curr["close"]) > float(curr["open"])
        and float(curr["close"]) > float(prev["open"])
        and float(curr["open"]) < float(prev["close"])
    )


def chart_probability(df: pd.DataFrame) -> int:
    score = 0

    trend = detect_trend(df)
    if trend == "UPTREND":
        score += 30

    if detect_breakout(df):
        score += 25

    if detect_pullback(df):
        score += 15

    if detect_bullish_engulfing(df):
        score += 20

    if "volume" in df.columns:
        vol20 = df["volume"].rolling(20).mean().iloc[-1]
        if pd.notna(vol20) and float(df["volume"].iloc[-1]) > 1.5 * float(vol20):
            score += 10

    return min(score, 95)