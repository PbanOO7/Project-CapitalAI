import pandas as pd
from database import (
    get_trades_df,
    get_portfolio_state,
    get_portfolio_rules,
    update_portfolio_state,
)
import streamlit as st

BASE_RISK = float(st.secrets.get("BASE_RISK", 0.02))


def calculate_portfolio_metrics() -> dict:
    state = get_portfolio_state()
    rules = get_portfolio_rules()
    trades = get_trades_df()

    starting_capital = float(state["starting_capital"])
    peak_equity = float(state["peak_equity"])

    closed = trades[trades["status"] == "CLOSED"].copy() if not trades.empty else pd.DataFrame()
    active = trades[trades["status"] == "ACTIVE"].copy() if not trades.empty else pd.DataFrame()

    realized_pnl = float(closed["pnl"].sum()) if not closed.empty else 0.0
    current_equity = starting_capital + realized_pnl

    if current_equity > peak_equity:
        peak_equity = current_equity

    drawdown = 0.0
    if peak_equity > 0:
        drawdown = (current_equity - peak_equity) / peak_equity

    current_exposure = float(
        (active["entry_price"] * active["position_size"]).sum()
    ) if not active.empty else 0.0

    exposure_ratio = current_exposure / current_equity if current_equity > 0 else 0.0

    freeze_flag = bool(state["freeze_flag"])

    # Recompute freeze based on drawdown rules
    if drawdown <= -float(rules["freeze_threshold"]):
        freeze_flag = True
    elif drawdown > -float(rules["freeze_threshold"]):
        freeze_flag = False

    update_portfolio_state(
        current_equity=current_equity,
        peak_equity=peak_equity,
        freeze_flag=freeze_flag,
    )

    return {
        "starting_capital": starting_capital,
        "current_equity": current_equity,
        "peak_equity": peak_equity,
        "drawdown": drawdown,
        "freeze_flag": freeze_flag,
        "current_exposure": current_exposure,
        "exposure_ratio": exposure_ratio,
        "active_count": int(len(active)),
        "rules": rules,
    }


def get_allowed_risk_and_permission() -> dict:
    metrics = calculate_portfolio_metrics()
    rules = metrics["rules"]

    if metrics["freeze_flag"]:
        return {
            "allowed_risk": 0.0,
            "allowed": False,
            "reason": "Trading frozen due to drawdown threshold breach."
        }

    allowed_risk = BASE_RISK

    if metrics["drawdown"] <= -float(rules["reduce_threshold"]):
        allowed_risk = BASE_RISK * float(rules["reduced_risk_multiplier"])

    if metrics["exposure_ratio"] >= float(rules["max_exposure"]):
        return {
            "allowed_risk": allowed_risk,
            "allowed": False,
            "reason": "Max portfolio exposure reached."
        }

    if metrics["active_count"] >= int(rules["max_concurrent_trades"]):
        return {
            "allowed_risk": allowed_risk,
            "allowed": False,
            "reason": "Max concurrent trades reached."
        }

    return {
        "allowed_risk": allowed_risk,
        "allowed": True,
        "reason": "Trade allowed."
    }