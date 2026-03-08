import yfinance as yf


def fundamental_score(symbol: str) -> int:
    try:
        info = yf.Ticker(symbol).info
    except Exception:
        return 0

    score = 0

    pe = info.get("trailingPE")
    roe = info.get("returnOnEquity")
    debt = info.get("debtToEquity")

    try:
        if pe is not None and pe > 0 and pe < 30:
            score += 3
    except Exception:
        pass

    try:
        if roe is not None and roe > 0.15:
            score += 4
    except Exception:
        pass

    try:
        if debt is not None and debt < 1:
            score += 3
    except Exception:
        pass

    return min(score * 2, 10)