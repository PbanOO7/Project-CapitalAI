from sqlalchemy import text
from database import engine
import streamlit as st

BASE_RISK = float(st.secrets["BASE_RISK"])

def get_portfolio_state():
    with engine.connect() as conn:
        state = conn.execute(text("SELECT * FROM portfolio_state LIMIT 1")).fetchone()
        rules = conn.execute(text("SELECT * FROM portfolio_rules LIMIT 1")).fetchone()
    return state, rules

def calculate_drawdown(current_equity, peak_equity):
    return (current_equity - peak_equity) / peak_equity

def get_allowed_risk():
    state, rules = get_portfolio_state()
    if not state or not rules:
        return BASE_RISK, False

    drawdown = calculate_drawdown(state.current_equity, state.peak_equity)

    if drawdown <= -rules.freeze_threshold:
        return 0, True

    if drawdown <= -rules.reduce_threshold:
        return BASE_RISK * rules.reduced_risk_multiplier, False

    return BASE_RISK, False