# Algorithmic Trading Bot (Paper Trading)

A backtesting and signal-generation framework for systematic trading strategies, built on Alpaca's market data API. Implements and compares moving average crossover variants on both single tickers and a multi-asset portfolio with dynamic, volatility-based capital allocation.

## What this does

- Pulls historical daily price data for any stock ticker via Alpaca's API
- Backtests a **20-day / 50-day moving average crossover** strategy (long-only)
- Compares it against the same strategy with an **RSI filter** layered on top
- Includes a **200-day trend filter** variant (buy-side only) — currently disabled by default, see note below
- Runs a **multi-asset portfolio backtest** that allocates capital across tickers using **inverse-volatility weighting** (calmer tickers get more capital, volatile ones get less), with volatility measured on a separate training window to avoid lookahead bias
- Benchmarks every strategy against a simple **buy-and-hold** baseline
- Prints comparison tables and full trade logs

## Key findings

**RSI filtering is not a reliable net-positive.** Tested across SPY, AAPL, TSLA, NIO, and a 10-stock blue-chip basket (MSFT, JPM, XOM, JNJ, PG, KO, WMT, DIS, CAT, V): RSI helps on some tickers (blocks bad late entries, e.g. TSLA) and hurts on others (blocks the single best trade of the period, e.g. SPY, NIO, JNJ). No consistent edge — MA crossover is trend-following, while RSI overbought/oversold is fundamentally mean-reversion, so the two signals sometimes fight each other.

**Buy-and-hold outperformed every active strategy in every single test**, often by a wide margin. This reflects a real, sustained uptrend across most tested tickers during the backtest period — a reminder that timing entries/exits has a real cost when markets are trending steadily upward, and any time spent out of position to "avoid risk" also means missing gains.

**One outlier stock can dominate a small portfolio.** An early multi-asset test included MU (Micron), which had a genuine, extreme real-world rally (windows around 300-980%+ depending on the test window, driven by an AI-memory-chip demand surge) that swamped the entire portfolio's results, making the basket's performance say more about MU specifically than about the strategy. Lesson: verify extreme results are real before trusting them (checked via news search, confirmed legitimate), and use a broad, diversified basket so no single stock dominates the read.

**The 200-day trend filter is currently disabled — confirmed unfair to test with the current data window.** The filter requires 200 days of price history before it can produce a value at all; with the current 455-day fetch window (90-day training + 365-day test), the filter spent most or all of the test period unable to act, rather than genuinely judging trend direction. Verified this is a data-availability artifact (not a real trend rejection) by checking exact `trend_ma` values on blocked trades, and confirmed the pattern was consistent across 5 different tickers — in one case (MSFT) the filter never placed a single trade in the entire test window. The function (`generate_signals_trend_filtered`) is kept in the code but excluded from the default run. Revisiting this would require a meaningfully longer fetch window so the 200-day MA is already warmed up before the test period begins.

## Setup

```bash
git clone https://github.com/kmbruss/algorithm-trading-bot.git
cd algorithm-trading-bot

python3 -m venv venv
source venv/bin/activate      # Windows: .\venv\Scripts\Activate.ps1

pip install -r requirements.txt
```

Create a `.env` file (copy `.env.example`) with your Alpaca paper trading API keys:

```
ALPACA_API_KEY=your_key_here
ALPACA_SECRET_KEY=your_secret_here
```

Free paper trading keys are available at [alpaca.markets](https://alpaca.markets) — no funding or identity verification required for paper trading.

## Usage

**1. Fetch historical data for one or more tickers:**
```bash
python fetch_data.py
```
Prompts for ticker symbols one at a time (type `done` when finished). Fetches 455 days of daily OHLCV bars per ticker (365-day test window + 90-day training window for volatility) and saves to `data/{SYMBOL}_daily.csv`.

**2. Run a single-ticker backtest:**
```bash
python backtest.py
```
Prompts for one ticker symbol, runs plain MA crossover and RSI-filtered variants, compares both against buy-and-hold.

**3. Run a multi-asset portfolio backtest:**
```bash
python portfolio_backtest.py
```
Prompts for multiple ticker symbols one at a time (type `done` when finished). Splits each ticker's data into a 90-day training window (volatility calculation only) and the remaining test window (actual backtest). Allocates a $10,000 total starting balance across tickers using inverse-volatility weighting, runs plain and RSI-filtered strategies per ticker, and reports both per-ticker and portfolio-level results.

Note: data CSVs are not committed to this repo (regenerated on demand via `fetch_data.py`) — see `.gitignore`.

## Project structure

```
fetch_data.py          # Pulls historical daily bars from Alpaca, saves to data/
backtest.py            # Single-ticker: MA/RSI/trend signals, trade simulation, strategy comparison
portfolio_backtest.py  # Multi-ticker: volatility-based allocation, runs backtest.py functions per ticker, aggregates
requirements.txt       # Python dependencies
.env.example           # Template for required API keys (copy to .env, fill in real keys)
data/                  # Generated CSVs (gitignored, not committed)
```

## Known limitations

- No transaction costs or slippage modeled — real trading would erode returns, especially for strategies with many trades (one 10-ticker test produced 43 trades/year for plain crossover)
- Volatility allocation weights are static for the whole backtest, not periodically rebalanced
- 200-day trend filter needs a longer fetch window to be evaluated fairly (see Key Findings)
- Single-asset volatility weighting ignores correlation between tickers — true risk parity would account for how assets move together, not just their individual volatility

## Roadmap

- [ ] Fix data window to properly evaluate the 200-day trend filter
- [ ] Add basic transaction cost / slippage modeling
- [ ] News/sentiment signal layer using Claude
- [ ] Live paper trading execution via Alpaca's trading API
