import requests


def get_news_sentiment(symbol: str) -> int:
    query_symbol = symbol.replace(".NS", "")
    url = f"https://news.google.com/rss/search?q={query_symbol}+stock"

    try:
        response = requests.get(url, timeout=10)
        text = response.text.lower()
    except Exception:
        return 0

    bullish_words = ["growth", "profit", "upgrade", "expansion", "beat", "strong"]
    bearish_words = ["loss", "downgrade", "fraud", "decline", "lawsuit", "weak"]

    score = 0

    for word in bullish_words:
        if word in text:
            score += 3

    for word in bearish_words:
        if word in text:
            score -= 3

    return max(-15, min(score, 15))