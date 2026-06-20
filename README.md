# Algorithmic Trading Bot (Paper Trading)

A backtesting and signal-generation framework for systematic trading strategies, built on Alpaca's market data API. Currently implements and compares a moving average crossover strategy against an RSI-filtered variant.

## What this does

- Pulls historical daily price data for any stock ticker via Alpaca's API
- Backtests a **20-day / 50-day moving average crossover** strategy (long-only)
- Compares it against the same strategy with an **RSI filter** layered on top
- Benchmarks both against a simple **buy-and-hold** baseline
- Prints a side-by-side comparison table and full trade logs

## Key finding so far

RSI filtering (blocking buy signals when RSI ≥ 70, sell signals when RSI ≤ 30) does **not** uniformly improve performance. Tested across SPY, AAPL, TSLA, and NIO:

- Helped significantly on TSLA (blocked a bad late-entry buy) and AAPL
- Hurt significantly on SPY and NIO (blocked the single best trade of the period)

The takeaway: MA crossover is a trend-following strategy, while RSI overbought/oversold is fundamentally a mean-reversion signal. Stacking them naively means the filter sometimes fights the very trend the base strategy is trying to capture. RSI can't distinguish "exhausted rally about to reverse" from "strong move at the start of a real trend" using price action alone.

Also notable: buy-and-hold outperformed both active strategies on every tested ticker over this period — a reminder that timing entries/exits has a real cost during sustained uptrends.
