from datetime import datetime
import streamlit as st
from sqlalchemy import create_engine, text
import pandas as pd

DATABASE_URL = st.secrets["DATABASE_URL"]
STARTING_CAPITAL = float(st.secrets.get("STARTING_CAPITAL", 10000))
BASE_RISK = float(st.secrets.get("BASE_RISK", 0.02))

engine = create_engine(DATABASE_URL, pool_pre_ping=True)


def init_db() -> None:
    with engine.begin() as conn:
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS trades (
            id SERIAL PRIMARY KEY,
            symbol TEXT NOT NULL,
            entry_price DOUBLE PRECISION NOT NULL,
            stop_price DOUBLE PRECISION NOT NULL,
            position_size INTEGER NOT NULL,
            confidence INTEGER NOT NULL,
            status TEXT NOT NULL,
            entry_date TIMESTAMP NOT NULL,
            exit_price DOUBLE PRECISION,
            exit_date TIMESTAMP,
            pnl DOUBLE PRECISION
        )
        """))

        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS portfolio_state (
            id INTEGER PRIMARY KEY,
            starting_capital DOUBLE PRECISION NOT NULL,
            peak_equity DOUBLE PRECISION NOT NULL,
            current_equity DOUBLE PRECISION NOT NULL,
            freeze_flag BOOLEAN NOT NULL,
            last_updated TIMESTAMP NOT NULL
        )
        """))

        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS portfolio_rules (
            id INTEGER PRIMARY KEY,
            reduce_threshold DOUBLE PRECISION NOT NULL,
            freeze_threshold DOUBLE PRECISION NOT NULL,
            reduced_risk_multiplier DOUBLE PRECISION NOT NULL,
            max_exposure DOUBLE PRECISION NOT NULL,
            max_concurrent_trades INTEGER NOT NULL
        )
        """))

        # Seed defaults once
        state = conn.execute(text("SELECT COUNT(*) FROM portfolio_state")).scalar()
        if state == 0:
            conn.execute(text("""
            INSERT INTO portfolio_state (
                id, starting_capital, peak_equity, current_equity, freeze_flag, last_updated
            )
            VALUES (1, :starting_capital, :peak_equity, :current_equity, FALSE, :last_updated)
            """), {
                "starting_capital": STARTING_CAPITAL,
                "peak_equity": STARTING_CAPITAL,
                "current_equity": STARTING_CAPITAL,
                "last_updated": datetime.utcnow(),
            })

        rules = conn.execute(text("SELECT COUNT(*) FROM portfolio_rules")).scalar()
        if rules == 0:
            conn.execute(text("""
            INSERT INTO portfolio_rules (
                id, reduce_threshold, freeze_threshold, reduced_risk_multiplier,
                max_exposure, max_concurrent_trades
            )
            VALUES (1, 0.05, 0.08, 0.5, 0.40, 3)
            """))


def get_trades_df() -> pd.DataFrame:
    with engine.connect() as conn:
        result = conn.execute(text("SELECT * FROM trades ORDER BY entry_date DESC"))
        rows = result.fetchall()
        return pd.DataFrame(rows, columns=result.keys())


def get_active_trades_df() -> pd.DataFrame:
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT * FROM trades
            WHERE status = 'ACTIVE'
            ORDER BY entry_date DESC
        """))
        rows = result.fetchall()
        return pd.DataFrame(rows, columns=result.keys())


def add_trade(
    symbol: str,
    entry_price: float,
    stop_price: float,
    position_size: int,
    confidence: int,
) -> None:
    with engine.begin() as conn:
        conn.execute(text("""
        INSERT INTO trades (
            symbol, entry_price, stop_price, position_size,
            confidence, status, entry_date
        )
        VALUES (
            :symbol, :entry_price, :stop_price, :position_size,
            :confidence, 'ACTIVE', :entry_date
        )
        """), {
            "symbol": symbol,
            "entry_price": entry_price,
            "stop_price": stop_price,
            "position_size": position_size,
            "confidence": confidence,
            "entry_date": datetime.utcnow(),
        })


def close_trade(trade_id: int, exit_price: float) -> None:
    with engine.begin() as conn:
        trade = conn.execute(text("""
            SELECT id, entry_price, position_size
            FROM trades
            WHERE id = :trade_id AND status = 'ACTIVE'
        """), {"trade_id": trade_id}).fetchone()

        if not trade:
            return

        pnl = (exit_price - float(trade.entry_price)) * int(trade.position_size)

        conn.execute(text("""
            UPDATE trades
            SET exit_price = :exit_price,
                exit_date = :exit_date,
                pnl = :pnl,
                status = 'CLOSED'
            WHERE id = :trade_id
        """), {
            "exit_price": exit_price,
            "exit_date": datetime.utcnow(),
            "pnl": pnl,
            "trade_id": trade_id,
        })


def get_portfolio_state() -> dict:
    with engine.connect() as conn:
        row = conn.execute(text("SELECT * FROM portfolio_state WHERE id = 1")).fetchone()
        return dict(row._mapping) if row else {}


def get_portfolio_rules() -> dict:
    with engine.connect() as conn:
        row = conn.execute(text("SELECT * FROM portfolio_rules WHERE id = 1")).fetchone()
        return dict(row._mapping) if row else {}


def update_portfolio_state(current_equity: float, peak_equity: float, freeze_flag: bool) -> None:
    with engine.begin() as conn:
        conn.execute(text("""
            UPDATE portfolio_state
            SET current_equity = :current_equity,
                peak_equity = :peak_equity,
                freeze_flag = :freeze_flag,
                last_updated = :last_updated
            WHERE id = 1
        """), {
            "current_equity": current_equity,
            "peak_equity": peak_equity,
            "freeze_flag": freeze_flag,
            "last_updated": datetime.utcnow(),
        })


def update_portfolio_rules(
    reduce_threshold: float,
    freeze_threshold: float,
    reduced_risk_multiplier: float,
    max_exposure: float,
    max_concurrent_trades: int,
) -> None:
    with engine.begin() as conn:
        conn.execute(text("""
            UPDATE portfolio_rules
            SET reduce_threshold = :reduce_threshold,
                freeze_threshold = :freeze_threshold,
                reduced_risk_multiplier = :reduced_risk_multiplier,
                max_exposure = :max_exposure,
                max_concurrent_trades = :max_concurrent_trades
            WHERE id = 1
        """), {
            "reduce_threshold": reduce_threshold,
            "freeze_threshold": freeze_threshold,
            "reduced_risk_multiplier": reduced_risk_multiplier,
            "max_exposure": max_exposure,
            "max_concurrent_trades": max_concurrent_trades,
        })