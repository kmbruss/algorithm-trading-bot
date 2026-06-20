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
    symbol = input("Enter ticker symbol (default SPY): ").strip().upper() or "SPY"
    print(f"Fetching {symbol} daily bars...")

    df = fetch_daily_bars(symbol, days_back=365)

    print(df.head())
    print(f"\nTotal rows: {len(df)}")

    output_path = f"{symbol}_daily.csv"
    df.to_csv(output_path)
    print(f"Saved to {output_path}")