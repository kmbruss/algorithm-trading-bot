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


def add_moving_averages(df: pd.DataFrame, short_window: int = 20, long_window: int = 50) -> pd.DataFrame:
    """
    Add short and long moving average columns to the DataFrame.
    Uses closing price as the basis for the average.
    """
    df["short_ma"] = df["close"].rolling(window=short_window).mean()
    df["long_ma"] = df["close"].rolling(window=long_window).mean()
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

    base_df = load_data(f"{symbol}_daily.csv")
    base_df = add_moving_averages(base_df, short_window=20, long_window=50)
    base_df = add_rsi(base_df, window=14)

    # Run each strategy variant on its own copy of the data
    plain_df = generate_signals_plain(base_df)
    rsi_df = generate_signals_rsi_filtered(base_df, rsi_overbought=70, rsi_oversold=30)

    plain_results = simulate_trades(plain_df, starting_cash=starting_cash)
    rsi_results = simulate_trades(rsi_df, starting_cash=starting_cash)
    baseline = buy_and_hold_baseline(base_df, starting_cash=starting_cash)

    # --- Comparison table ---
    print(f"\n{'Strategy':<25} {'Final Value':>15} {'Return %':>10} {'# Trades':>10}")
    print("-" * 62)
    print(f"{'MA Crossover (plain)':<25} ${plain_results['final_value']:>13,.2f} {plain_results['total_return_pct']:>9.2f}% {plain_results['num_trades']:>10}")
    print(f"{'MA Crossover + RSI':<25} ${rsi_results['final_value']:>13,.2f} {rsi_results['total_return_pct']:>9.2f}% {rsi_results['num_trades']:>10}")
    print(f"{'Buy & Hold':<25} ${baseline['final_value']:>13,.2f} {baseline['total_return_pct']:>9.2f}% {'-':>10}")

    # --- Trade logs for the two active strategies ---
    print(f"\n--- Plain MA Crossover trades ---")
    for trade in plain_results["trade_log"]:
        print(f"{trade['date'].date()}  {trade['action']:4s}  price=${trade['price']:.2f}")

    print(f"\n--- RSI-filtered trades ---")
    for trade in rsi_results["trade_log"]:
        print(f"{trade['date'].date()}  {trade['action']:4s}  price=${trade['price']:.2f}")