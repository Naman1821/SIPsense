"""
SIPsense — Data extraction and synthetic sentiment simulation.
Downloads Nifty 50 and Gold futures, generates realistic sentiment scores,
and exports a merged dataset to market_data.csv.
"""

from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

DATA_DIR = Path(__file__).resolve().parent
OUTPUT_CSV = DATA_DIR / "market_data.csv"

NIFTY_TICKER = "^NSEI"
GOLD_TICKER = "GC=F"
YEARS = 5
RANDOM_SEED = 42


def download_market_data(years: int = YEARS) -> pd.DataFrame:
    """Download daily closing prices for Nifty 50 and Gold futures."""
    end = pd.Timestamp.today().normalize()
    start = end - pd.DateOffset(years=years)

    nifty = yf.download(
        NIFTY_TICKER,
        start=start,
        end=end,
        progress=False,
        auto_adjust=True,
    )
    gold = yf.download(
        GOLD_TICKER,
        start=start,
        end=end,
        progress=False,
        auto_adjust=True,
    )

    def _close_series(df: pd.DataFrame, name: str) -> pd.Series:
        if isinstance(df.columns, pd.MultiIndex):
            close = df["Close"].iloc[:, 0] if df["Close"].ndim > 1 else df["Close"]
        else:
            close = df["Close"]
        return close.squeeze().rename(name)

    nifty_close = _close_series(nifty, "Nifty_Close")
    gold_close = _close_series(gold, "Gold_Close")

    prices = pd.concat([nifty_close, gold_close], axis=1, sort=True)
    prices.index = pd.to_datetime(prices.index).normalize()
    prices = prices.sort_index().dropna(how="all")

    # Align on union of trading dates; forward-fill short gaps (holidays)
    prices = prices.ffill().dropna()
    return prices


def generate_sentiment_scores(
    dates: pd.DatetimeIndex,
    n_shocks: int = 12,
    shock_magnitude: float = -0.92,
    seed: int = RANDOM_SEED,
) -> pd.Series:
    """
    Generate synthetic daily sentiment (-1.0 to 1.0) with realistic autocorrelation
    and deliberate market shocks on random dates.
    """
    rng = np.random.default_rng(seed)
    n = len(dates)

    # Ornstein-Uhlenbeck-like mean-reverting noise
    ar = np.zeros(n)
    innovation = rng.normal(0, 0.08, n)
    for i in range(1, n):
        ar[i] = 0.92 * ar[i - 1] + innovation[i]

    # Slow macro drift
    drift = 0.15 * np.sin(np.linspace(0, 4 * np.pi, n))
    base = np.clip(ar + drift, -1.0, 1.0)

    # Random severe negative shocks
    shock_idx = rng.choice(n, size=min(n_shocks, n), replace=False)
    base[shock_idx] = shock_magnitude + rng.normal(0, 0.05, len(shock_idx))
    base = np.clip(base, -1.0, 1.0)

    return pd.Series(base, index=dates, name="Sentiment_Score")


def build_market_dataframe(years: int = YEARS) -> pd.DataFrame:
    """Merge prices and sentiment into a single clean DataFrame."""
    prices = download_market_data(years=years)
    sentiment = generate_sentiment_scores(prices.index)

    df = prices.join(sentiment, how="inner")
    df.index.name = "Date"
    df = df.reset_index()
    return df


def export_market_data(output_path: Path = OUTPUT_CSV, years: int = YEARS) -> Path:
    """Build dataset and write to CSV."""
    df = build_market_dataframe(years=years)
    df.to_csv(output_path, index=False)
    print(f"Exported {len(df)} rows to {output_path}")
    return output_path


if __name__ == "__main__":
    export_market_data()
