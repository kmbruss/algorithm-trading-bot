import os
from datetime import datetime, timedelta

import pandas as pd
from dotenv import load_dotenv
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame

load_dotenv()
API_KEY = os.getenv("ALPACA_API_KEY")
SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")

def fetch_daily_bars(symbol: str, days_back: int = 365) -> pd.DataFrame:
    client = StockHistoricalDataClient(API_KEY, SECRET_KEY)
    end = datetime.now()
    start = end - timedelta(days=days_back)
    request = StockBarsRequest(
        symbol_or_symbols=symbol,
        timeframe=TimeFrame.Day,
        start=start,
        end=end,
    )
    bars = client.get_stock_bars(request)
    df = bars.df.reset_index(level=0, drop=True)
    return df

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

    for symbol in symbols:
        print(f"\nFetching {symbol} daily bars...")

        # 455 days = 90 days of training history (for volatility weighting)
        # + 365 days of actual backtest window
        df = fetch_daily_bars(symbol, days_back=455)

        print(df.head())
        print(f"Total rows: {len(df)}")

        output_path = f"data/{symbol}_daily.csv"
        df.to_csv(output_path)
        print(f"Saved to {output_path}")