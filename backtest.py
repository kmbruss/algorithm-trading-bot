"""
backtest.py

Backtests multiple moving average crossover strategy variants
against historical price data, and compares them to a simple
buy-and-hold baseline.
"""

import pandas as pd


def load_data(csv_path: str) -> pd.DataFrame:
    """Load price data saved by fetch_data.py."""
    df = pd.read_csv(csv_path, index_col="timestamp", parse_dates=True)
    return df


def add_moving_averages(df: pd.DataFrame, short_window: int = 20, long_window: int = 50, trend_window: int = 200) -> pd.DataFrame:
    """
    Add short and long moving average columns to the DataFrame.
    Uses closing price as the basis for the average.
    """
    df["short_ma"] = df["close"].rolling(window=short_window).mean()
    df["long_ma"] = df["close"].rolling(window=long_window).mean()
    df["trend_ma"] = df["close"].rolling(window=trend_window).mean()
    return df


def add_rsi(df: pd.DataFrame, window: int = 14) -> pd.DataFrame:
    """
    Add an RSI (Relative Strength Index) column.

    RSI measures whether price has moved too far too fast in one
    direction over the last `window` days. Scaled 0-100:
        RSI >= 70 -> "overbought" (big recent run-up)
        RSI <= 30 -> "oversold"   (big recent drop)
    """
    delta = df["close"].diff()

    gains = delta.clip(lower=0)
    losses = -delta.clip(upper=0)

    avg_gain = gains.rolling(window=window).mean()
    avg_loss = losses.rolling(window=window).mean()

    rs = avg_gain / avg_loss
    df["rsi"] = 100 - (100 / (1 + rs))
    return df


def generate_signals_plain(df: pd.DataFrame) -> pd.DataFrame:
    """
    Variant 1: Plain MA crossover, no filter.

    signal: 1 -> short MA above long MA (want to hold), 0 -> want cash
    position_change: +1 on the day signal flips to buy, -1 on flip to sell
    """
    df = df.copy()
    df["signal"] = 0
    df.loc[df["short_ma"] > df["long_ma"], "signal"] = 1
    df["position_change"] = df["signal"].diff()
    return df


def generate_signals_rsi_filtered(df: pd.DataFrame, rsi_overbought: float = 70, rsi_oversold: float = 30) -> pd.DataFrame:
    """
    Variant 2: MA crossover with an RSI filter on top.

    Same crossover logic as the plain version, but:
        - Suppress a buy signal if RSI is already overbought (>= rsi_overbought)
        - Suppress a sell signal if RSI is already oversold (<= rsi_oversold)
    """
    df = df.copy()
    df["signal"] = 0
    df.loc[df["short_ma"] > df["long_ma"], "signal"] = 1
    df["position_change"] = df["signal"].diff()

    overbought_buy = (df["position_change"] == 1) & (df["rsi"] >= rsi_overbought)
    oversold_sell = (df["position_change"] == -1) & (df["rsi"] <= rsi_oversold)
    df.loc[overbought_buy | oversold_sell, "position_change"] = 0

    return df

#unused
def generate_signals_trend_filtered(df: pd.DataFrame) -> pd.DataFrame:
    """
    Variant 3: MA crossover with a 200-day trend filter on the BUY side only.

    Same crossover logic as the plain version, but:
        - Suppress a buy signal unless price is also above the 200-day MA
          (i.e. only buy if we're in a confirmed longer-term uptrend)

    Sell signals are untouched -- exits happen on every death cross
    regardless of where price sits relative to the 200-day MA.
    """
    df = df.copy()
    df["signal"] = 0
    df.loc[df["short_ma"] > df["long_ma"], "signal"] = 1
    df["position_change"] = df["signal"].diff()

    # Suppress buy signals where price is below the 200-day trend MA,
    # or where the trend MA isn't available yet (not enough history).
    buy_against_trend = (df["position_change"] == 1) & (
        (df["close"] < df["trend_ma"]) | df["trend_ma"].isna()
    )
    df.loc[buy_against_trend, "position_change"] = 0

    return df

def simulate_trades(df: pd.DataFrame, starting_cash: float = 10000.0) -> dict:
    """
    Walk through the data day by day, simulating buying/selling based
    on the signal column. Returns a summary of how the strategy performed.
    """
    cash = starting_cash
    shares = 0
    trade_log = []

    for date, row in df.iterrows():
        price = row["close"]

        if row["position_change"] == 1 and shares == 0:
            shares = cash / price
            cash = 0
            trade_log.append({"date": date, "action": "BUY", "price": price, "shares": shares})

        elif row["position_change"] == -1 and shares > 0:
            cash = shares * price
            trade_log.append({"date": date, "action": "SELL", "price": price, "shares": shares})
            shares = 0

    final_price = df["close"].iloc[-1]
    final_value = cash + (shares * final_price)

    return {
        "starting_cash": starting_cash,
        "final_value": final_value,
        "total_return_pct": (final_value - starting_cash) / starting_cash * 100,
        "num_trades": len(trade_log),
        "trade_log": trade_log,
    }


def simulate_trades_long_short(df: pd.DataFrame, starting_cash: float = 10000) -> dict:
    """
    Same as simulate_trades(), but allows short positions instead of just
    exiting to cash on a death cross. This is a "stop-and-reverse" strategy:
    every crossover flips the position from long to short or vice versa.

    Tracks three possible states: long (own shares), short (owe shares,
    holding the cash from selling them), or flat (only used at the very
    start, before the first signal).
    """
    cash = starting_cash
    shares_long = 0
    shares_short = 0
    trade_log = []

    for date, row in df.iterrows():
        price = row["close"]

        if row["position_change"] == 1:
            if shares_short > 0:
                cost_to_cover = shares_short * price
                cash -= cost_to_cover
                trade_log.append({"date": date, "action": "COVER_SHORT", "price": price, "shares": shares_short})
                shares_short = 0
            if shares_long == 0:
                shares_long = cash / price
                cash = 0
                trade_log.append({"date": date, "action": "BUY", "price": price, "shares": shares_long})
       
        elif row["position_change"] == -1:
            if shares_long > 0:
                cash = shares_long * price
                trade_log.append({"date": date, "action": "SELL", "price": price, "shares": shares_long})
                shares_long = 0
            
            if shares_short == 0:
                shares_short = cash / price
                cash += shares_short * price
                trade_log.append({"date": date, "action": "SHORT", "price": price, "shares": shares_short})

        final_price = df["close"].iloc[-1]
        if shares_long > 0:
            final_value = cash + (shares_long * final_price)
        elif shares_short > 0:
            final_value = cash - (shares_short * final_price)
        else:
            final_value = cash

    return {
    "starting_cash": starting_cash,
    "final_value": final_value,
    "total_return_pct": (final_value - starting_cash) / starting_cash * 100,
    "num_trades": len(trade_log),
    "trade_log": trade_log,
    }

def buy_and_hold_baseline(df: pd.DataFrame, starting_cash: float = 10000.0) -> dict:
    """
    Baseline comparison: what if you just bought on day 1 and held
    until the last day, no trading at all?
    """
    first_price = df["close"].iloc[0]
    final_price = df["close"].iloc[-1]
    shares = starting_cash / first_price
    final_value = shares * final_price

    return {
        "starting_cash": starting_cash,
        "final_value": final_value,
        "total_return_pct": (final_value - starting_cash) / starting_cash * 100,
    }



if __name__ == "__main__":
    symbol = input("Enter ticker symbol (default SPY): ").strip().upper() or "SPY"
    starting_cash = 10000.0

    base_df = load_data(f"data/{symbol}_daily.csv")
    base_df = add_moving_averages(base_df, short_window=20, long_window=50, trend_window=200)
    base_df = add_rsi(base_df, window=14)

    plain_df = generate_signals_plain(base_df)
    rsi_df = generate_signals_rsi_filtered(base_df, rsi_overbought=70, rsi_oversold=30)
    #trend_df = generate_signals_trend_filtered(base_df)

    plain_results = simulate_trades(plain_df, starting_cash=starting_cash)
    rsi_results = simulate_trades(rsi_df, starting_cash=starting_cash)
    #trend_results = simulate_trades(trend_df, starting_cash=starting_cash)
    long_short_results = simulate_trades_long_short(plain_df, starting_cash=starting_cash)
    baseline = buy_and_hold_baseline(base_df, starting_cash=starting_cash)

    print(f"\n{'Strategy':<25} {'Final Value':>15} {'Return %':>10} {'# Trades':>10}")
    print("-" * 62)
    print(f"{'MA Crossover (plain)':<25} ${plain_results['final_value']:>13,.2f} {plain_results['total_return_pct']:>9.2f}% {plain_results['num_trades']:>10}")
    print(f"{'MA Crossover + RSI':<25} ${rsi_results['final_value']:>13,.2f} {rsi_results['total_return_pct']:>9.2f}% {rsi_results['num_trades']:>10}")
    #print(f"{'MA Crossover + Trend':<25} ${trend_results['final_value']:>13,.2f} {trend_results['total_return_pct']:>9.2f}% {trend_results['num_trades']:>10}")
    print(f"{'MA Crossover (long/short)':<25} ${long_short_results['final_value']:>13,.2f} {long_short_results['total_return_pct']:>9.2f}% {long_short_results['num_trades']:>10}")
    print(f"{'Buy & Hold':<25} ${baseline['final_value']:>13,.2f} {baseline['total_return_pct']:>9.2f}% {'-':>10}")

    print(f"\n--- Plain MA Crossover trades ---")
    for trade in plain_results["trade_log"]:
        print(f"{trade['date'].date()}  {trade['action']:4s}  price=${trade['price']:.2f}")

    print(f"\n--- RSI-filtered trades ---")
    for trade in rsi_results["trade_log"]:
        print(f"{trade['date'].date()}  {trade['action']:4s}  price=${trade['price']:.2f}")

    # print(f"\n--- Trend-filtered trades ---")
    # for trade in trend_results["trade_log"]:
    #     print(f"{trade['date'].date()}  {trade['action']:4s}  price=${trade['price']:.2f}")