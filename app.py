import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

import database
from capitalai import calculate_portfolio_metrics, get_allowed_risk_and_permission
from execution import calculate_position_size, record_paper_trade
from signal_engine import compute_signal, scan_universe

st.set_page_config(layout="wide", page_title="Project-CapitalAI")
st.title("🧠 Project-CapitalAI")

database.init_db()
STARTING_CAPITAL = float(st.secrets.get("STARTING_CAPITAL", 10000))

tab1, tab2, tab3, tab4 = st.tabs([
    "Signal Scanner",
    "Portfolio Dashboard",
    "Trade Journal",
    "Risk Controls",
])

with tab1:
    st.subheader("Signal Scanner")

    mode = st.radio("Mode", ["Universe Scan", "Single Symbol"], horizontal=True)

    if mode == "Single Symbol":
        symbol = st.text_input("Stock Symbol", value="NTPC.NS")

        if st.button("Run Signal"):
            signal = compute_signal(symbol)

            if not signal:
                st.warning("No usable signal found.")
            else:
                st.json(signal)

                decision = get_allowed_risk_and_permission()
                metrics = calculate_portfolio_metrics()

                if not decision["allowed"]:
                    st.error(decision["reason"])
                else:
                    shares = calculate_position_size(
                        capital=metrics["current_equity"],
                        allowed_risk=decision["allowed_risk"],
                        entry=signal["entry"],
                        stop=signal["stop"],
                    )

                    st.write(f"Allowed Risk: {decision['allowed_risk']*100:.2f}%")
                    st.write(f"Position Size: {shares} shares")

                    if shares <= 0:
                        st.warning("Position size calculated as zero.")
                    else:
                        if st.button("Record Paper Trade"):
                            record_paper_trade(
                                symbol=signal["symbol"],
                                entry=signal["entry"],
                                stop=signal["stop"],
                                target=signal["target"],
                                shares=shares,
                                confidence=signal["confidence"],
                            )
                            st.success("Paper trade recorded.")

    else:
        if st.button("Scan Universe"):
            df_signals = scan_universe()

            if df_signals.empty:
                st.warning("No signals found in the current universe.")
            else:
                st.dataframe(df_signals, use_container_width=True)

                top = df_signals.iloc[0].to_dict()
                decision = get_allowed_risk_and_permission()
                metrics = calculate_portfolio_metrics()

                st.markdown("### Top Candidate")
                st.json(top)

                if not decision["allowed"]:
                    st.error(decision["reason"])
                else:
                    shares = calculate_position_size(
                        capital=metrics["current_equity"],
                        allowed_risk=decision["allowed_risk"],
                        entry=float(top["entry"]),
                        stop=float(top["stop"]),
                    )

                    st.write(f"Allowed Risk: {decision['allowed_risk']*100:.2f}%")
                    st.write(f"Position Size: {shares} shares")

                    if shares > 0 and st.button("Record Top Paper Trade"):
                        record_paper_trade(
                            symbol=str(top["symbol"]),
                            entry=float(top["entry"]),
                            stop=float(top["stop"]),
                            target=float(top["target"]),
                            shares=shares,
                            confidence=int(top["confidence"]),
                        )
                        st.success("Top signal recorded as paper trade.")

with tab2:
    st.subheader("Portfolio Dashboard")

    metrics = calculate_portfolio_metrics()
    trades = database.get_trades_df()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Current Equity", f"₹{metrics['current_equity']:.2f}")
    col2.metric("Peak Equity", f"₹{metrics['peak_equity']:.2f}")
    col3.metric("Drawdown", f"{metrics['drawdown']*100:.2f}%")
    col4.metric("Exposure", f"₹{metrics['current_exposure']:.2f}")

    col5, col6, col7 = st.columns(3)
    col5.metric("Exposure Ratio", f"{metrics['exposure_ratio']*100:.2f}%")
    col6.metric("Active Trades", str(metrics["active_count"]))
    col7.metric("Freeze Flag", "ON" if metrics["freeze_flag"] else "OFF")

    closed = trades[trades["status"] == "CLOSED"].copy() if not trades.empty else pd.DataFrame()

    if not closed.empty:
        closed["entry_date"] = pd.to_datetime(closed["entry_date"])
        closed["exit_date"] = pd.to_datetime(closed["exit_date"])
        closed["pnl"] = pd.to_numeric(closed["pnl"], errors="coerce").fillna(0.0)
        closed = closed.sort_values("exit_date")

        closed["cum_pnl"] = closed["pnl"].cumsum()
        closed["equity"] = STARTING_CAPITAL + closed["cum_pnl"]
        closed["peak"] = closed["equity"].cummax()
        closed["drawdown"] = (closed["equity"] - closed["peak"]) / closed["peak"]

        wins = closed[closed["pnl"] > 0]
        losses = closed[closed["pnl"] < 0]

        st.markdown("### Performance Metrics")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Closed Trades", len(closed))
        c2.metric("Win Rate", f"{(len(wins)/len(closed))*100:.2f}%")
        c3.metric("Expectancy", f"₹{closed['pnl'].mean():.2f}")
        pf = wins["pnl"].sum() / abs(losses["pnl"].sum()) if not losses.empty else float("inf")
        c4.metric("Profit Factor", "∞" if pf == float("inf") else f"{pf:.2f}")

        st.markdown("### Equity Curve")
        fig = plt.figure()
        plt.plot(closed["exit_date"], closed["equity"])
        plt.xticks(rotation=30)
        plt.ylabel("Equity (₹)")
        plt.xlabel("Date")
        st.pyplot(fig)

        st.markdown("### Drawdown Curve")
        fig2 = plt.figure()
        plt.plot(closed["exit_date"], closed["drawdown"] * 100)
        plt.xticks(rotation=30)
        plt.ylabel("Drawdown %")
        plt.xlabel("Date")
        st.pyplot(fig2)
    else:
        st.info("No closed trades yet. Close trades to populate equity analytics.")

with tab3:
    st.subheader("Trade Journal")
    trades = database.get_trades_df()

    if trades.empty:
        st.info("No trades recorded yet.")
    else:
        st.dataframe(trades, use_container_width=True)

        active = trades[trades["status"] == "ACTIVE"].copy()
        if not active.empty:
            st.markdown("### Manually Close Active Trade")
            trade_id = st.selectbox("Select Trade ID", active["id"].tolist())
            exit_price = st.number_input("Exit Price", min_value=0.0, value=0.0, step=0.1)

            if st.button("Close Trade"):
                if exit_price <= 0:
                    st.warning("Please enter a valid exit price.")
                else:
                    database.close_trade(int(trade_id), float(exit_price))
                    st.success("Trade closed.")

with tab4:
    st.subheader("Risk Controls")

    rules = database.get_portfolio_rules()

    reduce_threshold = st.slider(
        "Reduce Risk Threshold (Drawdown %)",
        min_value=1,
        max_value=20,
        value=int(float(rules["reduce_threshold"]) * 100),
    )
    freeze_threshold = st.slider(
        "Freeze Threshold (Drawdown %)",
        min_value=2,
        max_value=30,
        value=int(float(rules["freeze_threshold"]) * 100),
    )
    reduced_risk_multiplier = st.slider(
        "Reduced Risk Multiplier",
        min_value=0.1,
        max_value=1.0,
        value=float(rules["reduced_risk_multiplier"]),
        step=0.1,
    )
    max_exposure = st.slider(
        "Max Portfolio Exposure (%)",
        min_value=10,
        max_value=100,
        value=int(float(rules["max_exposure"]) * 100),
    )
    max_concurrent_trades = st.slider(
        "Max Concurrent Trades",
        min_value=1,
        max_value=10,
        value=int(rules["max_concurrent_trades"]),
    )

    if st.button("Save Risk Rules"):
        database.update_portfolio_rules(
            reduce_threshold=reduce_threshold / 100,
            freeze_threshold=freeze_threshold / 100,
            reduced_risk_multiplier=reduced_risk_multiplier,
            max_exposure=max_exposure / 100,
            max_concurrent_trades=max_concurrent_trades,
        )
        st.success("Risk rules updated.")