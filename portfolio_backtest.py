"""
portfolio_backtest.py

Runs the MA crossover strategy (plain and RSI-filtered) across multiple
tickers simultaneously, allocating starting capital dynamically based on
each ticker's historical volatility (inverse-volatility weighting).

Volatility is measured on a separate, earlier "training" window so that
allocation weights never use information from the actual backtest period
(avoids lookahead bias).
"""

import pandas as pd

from backtest import (
    add_moving_averages,
    add_rsi,
    generate_signals_plain,
    generate_signals_rsi_filtered,
    simulate_trades,
    buy_and_hold_baseline,
)

TRAINING_WINDOW_DAYS = 90

def load_full_data(symbol: str) -> pd.DataFrame:
    """Load the full CSV (training window + test window combined)."""
    path = f"data/{symbol}_daily.csv"
    df = pd.read_csv(path, index_col="timestamp", parse_dates=True)
    return df

def split_training_and_test(df: pd.DataFrame, training_days: int = TRAINING_WINDOW_DAYS) -> tuple:
    """
    Split a full price history into:
        - training_df: the earliest `training_days` rows (used ONLY for
          calculating volatility / allocation weights)
        - test_df: everything after that (the actual backtest period)
    """
    training_df = df.iloc[:training_days].copy()
    test_df = df.iloc[training_days:].copy()
    return training_df, test_df

def calculate_volatility(training_df: pd.DataFrame) -> float:
    """
    Calculate daily-return volatility (standard deviation) over the
    training window. Higher value = more volatile / riskier ticker.
    """
    daily_returns = training_df["close"].pct_change()
    volatility = daily_returns.std()
    return volatility

def calculate_inverse_vol_weights(volatilities: dict) -> dict:
    """
    Convert a dict of {symbol: volatility} into a dict of
    {symbol: weight} using inverse-volatility weighting.

    Lower volatility -> higher weight (more capital allocated).
    Weights sum to 1.0 across all symbols.
    """
    raw_weights = {symbol: 1 / vol for symbol, vol in volatilities.items()}
    total = sum(raw_weights.values())
    weights = {symbol: raw / total for symbol, raw in raw_weights.items()}
    return weights

if __name__ == "__main__":
    
    symbols = []
    while True:
        user_input = input("Enter ticker symbol (or 'done' to finish): ").strip().upper()
        if user_input == "DONE":
            if not symbols:
                print("you haven't entered any tickers yet")
                continue
            break
        if user_input:
            symbols.append(user_input)

    total_starting_cash = 10000.0

     # --- Step 1: load data and split into training/test per ticker ---
    training_data = {}
    test_data = {}

    for symbol in symbols:
        full_df = load_full_data(symbol)
        training_df, test_df = split_training_and_test(full_df)
        training_data[symbol] = training_df
        test_data[symbol] = test_df
    
    # --- Step 2: calculate volatility per ticker (training window only) ---
    volatilities = {symbol: calculate_volatility(training_data[symbol]) for symbol in symbols}

    # --- Step 3: convert volatility into allocation weights ---
    weights = calculate_inverse_vol_weights(volatilities)

    print(f"\n{'Symbol':<8} {'Volatility':>12} {'Weight':>10} {'Allocated $':>14}")
    print("-" * 48)
    for symbol in symbols:
        allocated_cash = weights[symbol] * total_starting_cash
        print(f"{symbol:<8} {volatilities[symbol]:>12.4f} {weights[symbol]:>9.1%} ${allocated_cash:>12,.2f}")

    plain_results_by_symbol = {}
    rsi_results_by_symbol = {}
    baseline_results_by_symbol = {}

    for symbol in symbols:
        allocated_cash = weights[symbol] * total_starting_cash

        df = test_data[symbol]
        df = add_moving_averages(df, short_window=20, long_window=50)
        df = add_rsi(df, window=14)

        plain_df = generate_signals_plain(df)
        rsi_df = generate_signals_rsi_filtered(df, rsi_overbought=80, rsi_oversold=20)

        plain_results_by_symbol[symbol] = simulate_trades(plain_df, starting_cash=allocated_cash)
        rsi_results_by_symbol[symbol] = simulate_trades(rsi_df, starting_cash=allocated_cash)
        baseline_results_by_symbol[symbol] = buy_and_hold_baseline(df, starting_cash=allocated_cash)

    # --- Step 5: aggregate into portfolio-level totals ---
    plain_total = sum(r["final_value"] for r in plain_results_by_symbol.values())
    rsi_total = sum(r["final_value"] for r in rsi_results_by_symbol.values())
    baseline_total = sum(r["final_value"] for r in baseline_results_by_symbol.values())

    plain_trades_total = sum(r["num_trades"] for r in plain_results_by_symbol.values())
    rsi_trades_total = sum(r["num_trades"] for r in rsi_results_by_symbol.values())

    def pct_return(final_value, starting=total_starting_cash):
        return (final_value - starting) / starting * 100

    # --- Per-ticker breakdown ---
    print(f"\n{'Symbol':<8} {'Plain Return':>13} {'RSI Return':>12} {'Buy&Hold Return':>16}")
    print("-" * 52)
    for symbol in symbols:
        plain_pct = pct_return(plain_results_by_symbol[symbol]["final_value"], weights[symbol] * total_starting_cash)
        rsi_pct = pct_return(rsi_results_by_symbol[symbol]["final_value"], weights[symbol] * total_starting_cash)
        bh_pct = pct_return(baseline_results_by_symbol[symbol]["final_value"], weights[symbol] * total_starting_cash)
        print(f"{symbol:<8} {plain_pct:>12.2f}% {rsi_pct:>11.2f}% {bh_pct:>15.2f}%")

    # --- Portfolio-level totals ---
    print(f"\n{'Portfolio Strategy':<25} {'Final Value':>15} {'Return %':>10} {'# Trades':>10}")
    print("-" * 62)
    print(f"{'MA Crossover (plain)':<25} ${plain_total:>13,.2f} {pct_return(plain_total):>9.2f}% {plain_trades_total:>10}")
    print(f"{'MA Crossover + RSI':<25} ${rsi_total:>13,.2f} {pct_return(rsi_total):>9.2f}% {rsi_trades_total:>10}")
    print(f"{'Buy & Hold (basket)':<25} ${baseline_total:>13,.2f} {pct_return(baseline_total):>9.2f}% {'-':>10}")