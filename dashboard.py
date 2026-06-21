"""
dashboard.py

A simple live dashboard that shows the current state of your existing
MA crossover / RSI indicators for one or more tickers, refreshed
periodically. This does NOT execute trades or tell you to buy/sell --
it shows you what the indicators are doing, in plain language, so you
can make your own decision.

Run with: streamlit run dashboard.py
"""

import streamlit as st
import pandas as pd
from streamlit_autorefresh import st_autorefresh

from fetch_data import fetch_daily_bars
from backtest import add_moving_averages, add_rsi

REFRESH_SECONDS = 300  # how often to pull fresh data (5 minutes)

# Streamlit-native auto-refresh: triggers a rerun every REFRESH_SECONDS
# without blocking the page render (unlike a manual time.sleep() + st.rerun()).
st_autorefresh(interval=REFRESH_SECONDS * 1000, key="data_refresh")


def get_indicator_snapshot(symbol: str) -> dict:
    """
    Fetch recent data for `symbol`, compute indicators, and return
    a plain dict summarizing the current state -- no trade decisions,
    just a readable snapshot of what the numbers are doing right now.
    """
    df = fetch_daily_bars(symbol, days_back=120)  # enough history for 50-day MA + buffer
    df = add_moving_averages(df, short_window=20, long_window=50)
    df = add_rsi(df, window=14)

    latest = df.iloc[-1]
    previous = df.iloc[-2]

    is_bullish_now = latest["short_ma"] > latest["long_ma"]
    was_bullish_before = previous["short_ma"] > previous["long_ma"]
    just_crossed = is_bullish_now != was_bullish_before

    if just_crossed:
        cross_note = "Golden cross just happened" if is_bullish_now else "Death cross just happened"
    else:
        cross_note = "No new crossover"

    rsi_value = latest["rsi"]
    if rsi_value >= 70:
        rsi_note = "Overbought (RSI >= 70)"
    elif rsi_value <= 30:
        rsi_note = "Oversold (RSI <= 30)"
    else:
        rsi_note = "Neutral range"

    return {
        "symbol": symbol,
        "price": latest["close"],
        "short_ma": latest["short_ma"],
        "long_ma": latest["long_ma"],
        "rsi": rsi_value,
        "trend": "Bullish (short MA above long MA)" if is_bullish_now else "Bearish (short MA below long MA)",
        "cross_note": cross_note,
        "rsi_note": rsi_note,
        "as_of": latest.name,
    }


st.set_page_config(page_title="Strategy Dashboard", layout="wide")
st.title("Indicator Dashboard")
st.caption("Shows current MA crossover and RSI state. This does not give buy/sell advice -- it's a read of where your indicators stand right now.")

symbols_input = st.text_input("Tickers (comma-separated)", value="SPY,AAPL")
symbols = [s.strip().upper() for s in symbols_input.split(",") if s.strip()]

st.write(f"Last updated: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}")
cols = st.columns(len(symbols)) if symbols else []

for col, symbol in zip(cols, symbols):
    with col:
        try:
            snap = get_indicator_snapshot(symbol)
            st.subheader(snap["symbol"])
            st.metric("Price", f"${snap['price']:.2f}")
            st.write(f"**Trend:** {snap['trend']}")
            st.write(f"**Crossover:** {snap['cross_note']}")
            st.write(f"**RSI:** {snap['rsi']:.1f} -- {snap['rsi_note']}")
            st.caption(f"As of {snap['as_of'].date()}")
        except Exception as e:
            st.error(f"Could not load {symbol}: {e}")