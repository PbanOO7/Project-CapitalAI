from sqlalchemy import create_engine, text
import streamlit as st

engine = create_engine(st.secrets["DATABASE_URL"])

def init_db():
    with engine.begin() as conn:
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS trades (
            id SERIAL PRIMARY KEY,
            symbol TEXT,
            entry_price FLOAT,
            stop_price FLOAT,
            position_size INT,
            confidence INT,
            status TEXT,
            entry_date TIMESTAMP,
            exit_price FLOAT,
            exit_date TIMESTAMP,
            pnl FLOAT
        )
        """))

        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS portfolio_state (
            id SERIAL PRIMARY KEY,
            starting_capital FLOAT,
            peak_equity FLOAT,
            current_equity FLOAT,
            freeze_flag BOOLEAN,
            last_updated TIMESTAMP DEFAULT NOW()
        )
        """))

        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS portfolio_rules (
            id SERIAL PRIMARY KEY,
            reduce_threshold FLOAT,
            freeze_threshold FLOAT,
            reduced_risk_multiplier FLOAT,
            max_exposure FLOAT,
            max_concurrent_trades INT
        )
        """))