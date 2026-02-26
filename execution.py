from database import engine
from sqlalchemy import text
from datetime import datetime

def open_trade(symbol, entry, stop, size, confidence):
    with engine.begin() as conn:
        conn.execute(text("""
        INSERT INTO trades
        (symbol, entry_price, stop_price, position_size,
         confidence, status, entry_date)
        VALUES
        (:symbol, :entry, :stop, :size, :confidence, 'ACTIVE', :now)
        """), {
            "symbol": symbol,
            "entry": entry,
            "stop": stop,
            "size": size,
            "confidence": confidence,
            "now": datetime.now()
        })