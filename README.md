# Algorithm Trading Bot

This is a backtesting project I built to learn how to design, test, and evaluate trading strategies. It pulls real historical stock data through Alpaca's API and tests a few different strategy variants against each other, including a basic moving average crossover, an RSI filter, a 200-day trend filter, and a long/short version. It also runs a multi-asset portfolio version that splits capital across tickers based on volatility instead of splitting it evenly.

The short version of what I found: none of the strategies reliably beat just buying and holding. That's not really a surprise once you dig into why, but getting to a trustworthy answer took catching a few real mistakes along the way, which is honestly the more interesting part of this project.

## What it actually does

- Pulls daily price data for any ticker from Alpaca and saves it locally
- Runs a 20-day / 50-day moving average crossover strategy, long only
- Adds an RSI filter on top to see if it improves things
- Adds a 200-day trend filter as a buy-side confirmation (more on this below, it's currently turned off by default)
- Adds a long/short version that shorts on a death cross instead of just sitting in cash
- Splits capital across multiple tickers using inverse volatility weighting, so calmer stocks get more money and volatile ones get less
- Compares everything against plain buy and hold
- A small Streamlit dashboard that shows the current state of these indicators for a ticker, refreshed every few minutes. It doesn't tell you to buy or sell anything, it just shows you what the numbers are doing.

## What I found

I tested across SPY, AAPL, TSLA, NIO, MSFT, JPM, and a 10-stock basket, mostly over a roughly one year window from mid 2025 to mid 2026. Buy and hold won almost every single time. Out of 10 comparisons, it lost exactly once, to the RSI-filtered version on TSLA.

That's a pretty boring sounding result, but it lines up with something that's actually well known: in a market that's mostly going up, trying to time your entries and exits usually costs you more than it saves, because you end up missing chunks of the rally while you're sitting in cash waiting for a new signal.

I also tested a 2022 window, which was a real bear market, to see if things looked different outside of a bull run. They did, somewhat. Buy and hold was still usually the best (or the least bad) option, but the gap was smaller, and on V the RSI filtered version actually beat buy and hold while buy and hold was losing money. The long/short version, though, was consistently the worst performer in both the bull and bear windows. Constantly flipping from long to short on every crossover seems to just compound whipsaw losses instead of catching the down moves cleanly, at least with this signal.

A few specific things worth calling out:

**RSI doesn't have a consistent effect.** It helped on some tickers and hurt on others, sometimes by a lot. The reason makes sense once you think about it: moving average crossover is a trend following idea, RSI overbought/oversold is a mean reversion idea, and those two things don't always agree. Sometimes RSI blocks a bad trade, sometimes it blocks the best trade of the year.

**One outlier stock can wreck a small portfolio's numbers.** Early on I ran a portfolio test that included Micron (MU), which had a real, enormous rally (somewhere around 300 to 980 percent depending on the exact window) because of AI chip demand. It completely dominated the portfolio's results, to the point where the numbers were really just telling me about Micron, not about the strategy. I checked the news to make sure it wasn't a data error before trusting it, then went with a more diversified basket instead.

**The 200-day trend filter is currently off by default because I don't think it's being tested fairly.** It needs 200 days of price history before it can even produce a number, and with my current data window that ate up most or all of the actual test period for some tickers. MSFT never placed a single trade under this filter in one test, which isn't really telling you anything about whether MSFT was trending, it's just telling you the filter never had enough data to turn on. I checked this directly by looking at the actual values instead of just trusting the final return number. The function is still in the code, I just don't run it by default until I fix the data window.

## Setup

```bash
git clone https://github.com/kmbruss/algorithm-trading-bot.git
cd algorithm-trading-bot

python3 -m venv venv
source venv/bin/activate      # Windows: .\venv\Scripts\Activate.ps1

pip install -r requirements.txt
```

Copy `.env.example` to `.env` and fill in your Alpaca paper trading keys: