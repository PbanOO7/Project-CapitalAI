from database import add_trade


def calculate_position_size(capital: float, allowed_risk: float, entry: float, stop: float) -> int:
    risk_amount = capital * allowed_risk
    risk_per_share = entry - stop

    if risk_per_share <= 0:
        return 0

    shares = int(risk_amount // risk_per_share)
    return max(shares, 0)


def record_paper_trade(
    symbol: str,
    entry: float,
    stop: float,
    target: float,
    shares: int,
    confidence: int,
) -> None:
    add_trade(
        symbol=symbol,
        entry_price=entry,
        stop_price=stop,
        target_price=target,
        position_size=shares,
        confidence=confidence,
    )