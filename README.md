# Algorithmic Trading Bot: A Backtesting Research Project

**Question investigated:** Can simple technical filters (RSI, 200-day trend confirmation) improve on a basic moving-average crossover strategy — and can either approach beat passive buy-and-hold — across individual stocks and a volatility-weighted multi-asset portfolio?

**Short answer: no.** Across 10 independent tests (9 single tickers + 1 ten-stock portfolio), buy-and-hold beat every active strategy variant every time but one. This is consistent with market efficiency and a sustained bull market over the test period, not a flaw in the implementation — see Results below for the full breakdown and Why This Still Matters for what the project actually demonstrates.

## What this does

- Pulls historical daily price data for any stock ticker via Alpaca's API
- Backtests a **20-day / 50-day moving average crossover** strategy (long-only)
- Compares it against the same strategy with an **RSI filter** layered on top
- Includes a **200-day trend filter** variant (buy-side only) — built and verified correct, but excluded from the default run; see Known Limitations
- Runs a **multi-asset portfolio backtest** allocating capital across tickers via **inverse-volatility weighting** (calmer tickers get more capital), with volatility measured on a separate training window to avoid lookahead bias
- Benchmarks every strategy against simple **buy-and-hold**

## Results

| Ticker | Plain MA | MA + RSI | Buy & Hold | Either beat B&H? |
|---|---|---|---|---|
| SPY | 12.09% | 6.35% | 25.65% | No |
| SPY (2nd window) | 21.30% | 15.08% | 30.08% | No |
| NIO | 9.08% | 1.10% | 47.21% | No |
| AAPL | 15.98% | 29.73% | 47.90% | No |
| TSLA | 2.38% | 22.32% | 14.86% | **RSI only** |
| TSLA (2nd window) | -10.48% | 6.96% | 43.86% | No |
| MSFT | -10.77% | -22.18% | -3.48% | No |
| JPM | 5.55% | 12.15% | 31.11% | No |
| **10-stock portfolio** (MSFT, JPM, XOM, JNJ, PG, KO, WMT, DIS, CAT, V), volatility-weighted | 8.20% | 5.70% | 18.27% | No |

**Score: buy-and-hold won 9 out of 10 tests.** Plain MA crossover never won. RSI-filtered crossover won exactly once.

## Why this still matters

A strategy that doesn't beat the market isn't a failed project — it's an expected, well-documented result, and producing it credibly requires real engineering:

- **RSI and MA crossover are philosophically opposed signals.** MA crossover is trend-following; RSI overbought/oversold is mean-reversion. Stacking them means the filter sometimes blocks the exact trade that would have worked (confirmed on SPY, NIO, JNJ) and sometimes correctly avoids a bad late entry (confirmed on TSLA). There's no consistent edge because the two signals are answering different questions.
- **One outlier can dominate a small portfolio.** An early multi-asset test included MU (Micron), which had a genuine ~300-980% real-world rally driven by AI-memory-chip demand. This swamped the whole portfolio's result. Confirmed via news search that the move was real, not a data bug — then excluded it in favor of a diversified basket where no single stock dominates the read.
- **Lookahead bias is easy to introduce by accident.** The portfolio's volatility weights are calculated on a 90-day training window strictly before the test window begins, so allocation never uses information that wouldn't have been available at the time.
- **Not every promising idea survives contact with real data.** The 200-day trend filter looked reasonable in design but, when tested across 5 tickers, was confirmed (by inspecting actual `trend_ma` values, not just final returns) to be mostly blocked by insufficient warm-up history rather than genuine trend rejection — in one case (MSFT) it placed zero trades in the entire test window. Recognizing and documenting that an idea needs more infrastructure before it can be fairly evaluated, rather than reporting a misleading result, is itself the point of doing this rigorously.

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
Prompts for multiple ticker symbols one at a time (type `done` when finished). Splits each ticker's data into a 90-day training window (volatility calculation only) and the remaining test window (actual backtest). Allocates a $10,000 total starting balance across tickers using inverse-volatility weighting, runs plain and RSI-filtered strategies per ticker, and reports per-ticker and portfolio-level results.

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

- No transaction costs or slippage modeled — real trading would erode returns further, especially for strategies with many trades (one 10-ticker test produced 43 trades/year for plain crossover)
- Volatility allocation weights are static for the whole backtest, not periodically rebalanced
- 200-day trend filter needs a longer fetch window to be evaluated fairly (see Why This Still Matters)
- Volatility weighting treats each ticker independently and ignores correlation between assets — true risk parity would account for how assets move together, not just their individual volatility
- All testing covers a single, strongly bullish ~1-year window; results may not generalize to bear or sideways markets

## Roadmap

- [ ] Fix data window to properly evaluate the 200-day trend filter
- [ ] Add basic transaction cost / slippage modeling
- [ ] News/sentiment signal layer using Claude
- [ ] Live paper trading execution via Alpaca's trading API