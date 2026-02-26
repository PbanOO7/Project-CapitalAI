import streamlit as st
from database import init_db
from signal_engine import compute_signal
from capitalai import get_allowed_risk
from execution import open_trade

st.set_page_config(layout="wide")
st.title("🧠 Project CapitalAI — Hedge Control Panel")

init_db()

symbol = st.text_input("Stock Symbol (e.g. NTPC.NS)")

if st.button("Run Signal"):
    signal = compute_signal(symbol)
    if not signal:
        st.warning("No data available")
    else:
        st.write(signal)

        allowed_risk, freeze = get_allowed_risk()

        if freeze:
            st.error("🚫 Trading Frozen (Drawdown Limit Hit)")
        else:
            st.success(f"Allowed Risk: {allowed_risk*100:.2f}%")

            capital = float(st.secrets["STARTING_CAPITAL"])
            risk_amount = capital * allowed_risk

            position_size = int(risk_amount / (signal["entry"] - signal["stop"]))

            st.write(f"Position Size: {position_size}")

            if st.button("Execute Trade"):
                open_trade(symbol,
                           signal["entry"],
                           signal["stop"],
                           position_size,
                           signal["confidence"])
                st.success("Trade Recorded")