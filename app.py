import streamlit as st
import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
import matplotlib.pyplot as plt

st.set_page_config(layout="wide")
st.title("📊 Project CapitalAI — Performance Dashboard")

DATABASE_URL = st.secrets["DATABASE_URL"]
STARTING_CAPITAL = float(st.secrets.get("STARTING_CAPITAL", 10000))

engine = create_engine(DATABASE_URL)

@st.cache_data
def load_trades():
    with engine.connect() as conn:
        result = conn.execute(text("SELECT * FROM trades ORDER BY entry_date"))
        df = pd.DataFrame(result.fetchall(), columns=result.keys())
    return df

df = load_trades()

if df.empty:
    st.warning("No trades found in database.")
    st.stop()

# Convert types
df["entry_date"] = pd.to_datetime(df["entry_date"])
df["exit_date"] = pd.to_datetime(df["exit_date"])
df["pnl"] = pd.to_numeric(df["pnl"], errors="coerce").fillna(0)

closed = df[df["status"] == "CLOSED"].copy()

if closed.empty:
    st.info("No closed trades yet.")
    st.stop()

# === KPI Calculations ===
total_trades = len(closed)
wins = closed[closed["pnl"] > 0]
losses = closed[closed["pnl"] < 0]

win_rate = len(wins) / total_trades if total_trades else 0
avg_win = wins["pnl"].mean() if not wins.empty else 0
avg_loss = losses["pnl"].mean() if not losses.empty else 0
gross_profit = wins["pnl"].sum()
gross_loss = abs(losses["pnl"].sum())
profit_factor = gross_profit / gross_loss if gross_loss > 0 else np.inf
expectancy = closed["pnl"].mean()

# === Equity Curve ===
closed = closed.sort_values("exit_date")
closed["cum_pnl"] = closed["pnl"].cumsum()
closed["equity"] = STARTING_CAPITAL + closed["cum_pnl"]
closed["peak"] = closed["equity"].cummax()
closed["drawdown"] = (closed["equity"] - closed["peak"]) / closed["peak"]

max_dd = closed["drawdown"].min()

# === Dashboard Layout ===
st.subheader("Performance Metrics")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Trades", total_trades)
col2.metric("Win Rate", f"{win_rate*100:.2f}%")
col3.metric("Profit Factor", f"{profit_factor:.2f}")
col4.metric("Expectancy (₹)", f"{expectancy:.2f}")

col5, col6, col7 = st.columns(3)
col5.metric("Avg Win (₹)", f"{avg_win:.2f}")
col6.metric("Avg Loss (₹)", f"{avg_loss:.2f}")
col7.metric("Max Drawdown (%)", f"{max_dd*100:.2f}%")

# === Equity Chart ===
st.subheader("Equity Curve")

fig = plt.figure()
plt.plot(closed["exit_date"], closed["equity"])
plt.xticks(rotation=45)
plt.ylabel("Equity (₹)")
plt.xlabel("Date")
st.pyplot(fig)

# === Drawdown Chart ===
st.subheader("Drawdown (%)")

fig2 = plt.figure()
plt.plot(closed["exit_date"], closed["drawdown"]*100)
plt.xticks(rotation=45)
plt.ylabel("Drawdown %")
plt.xlabel("Date")
st.pyplot(fig2)

# === Trade Journal ===
st.subheader("Closed Trade Journal")
st.dataframe(closed.sort_values("exit_date", ascending=False))