"""
SIPsense — SIP compounding, volatility, and sentiment impact analytics.
"""

from pathlib import Path

import numpy as np
import pandas as pd

DATA_DIR = Path(__file__).resolve().parent
MARKET_CSV = DATA_DIR / "market_data.csv"

SIP_AMOUNT_INR = 5_000
SEVERE_SHOCK_THRESHOLD = -0.8
SENTIMENT_LAG_DAYS = 3
VOLATILITY_WINDOW = 30


def load_market_data(csv_path: Path = MARKET_CSV) -> pd.DataFrame:
    """Load market data; ensure Date is datetime and sorted."""
    df = pd.read_csv(csv_path, parse_dates=["Date"])
    df = df.sort_values("Date").reset_index(drop=True)
    return df


def calculate_sip(
    df: pd.DataFrame,
    price_col: str,
    sip_amount: float = SIP_AMOUNT_INR,
    label: str = "Asset",
) -> pd.DataFrame:
    """
    Simulate monthly SIP on the 1st trading day of each month.
    Returns daily series with units, invested, and portfolio value.
    """
    df = df.copy()
    df = df.set_index("Date").sort_index()

    sip_dates: set = set()
    seen_months: set = set()
    for dt in df.index:
        ym = (dt.year, dt.month)
        if ym not in seen_months:
            seen_months.add(ym)
            sip_dates.add(dt)

    units = 0.0
    total_invested = 0.0
    records = []

    for dt, row in df.iterrows():
        if dt in sip_dates:
            price = row[price_col]
            if pd.notna(price) and price > 0:
                units += sip_amount / price
                total_invested += sip_amount

        price = row[price_col]
        portfolio_value = units * price if pd.notna(price) else np.nan

        records.append(
            {
                "Date": dt,
                f"{label}_Units": units,
                f"{label}_Invested": total_invested,
                f"{label}_Value": portfolio_value,
            }
        )

    return pd.DataFrame(records)


def calculate_combined_sip(df: pd.DataFrame, sip_amount: float = SIP_AMOUNT_INR) -> pd.DataFrame:
    """SIP into Nifty and Gold separately; combine portfolio metrics."""
    nifty_sip = calculate_sip(df, "Nifty_Close", sip_amount, "Nifty")
    gold_sip = calculate_sip(df, "Gold_Close", sip_amount, "Gold")

    result = df[["Date", "Nifty_Close", "Gold_Close", "Sentiment_Score"]].copy()
    result = result.merge(nifty_sip, on="Date")
    result = result.merge(gold_sip, on="Date")

    result["Total_Invested"] = result["Nifty_Invested"] + result["Gold_Invested"]
    result["Portfolio_Value"] = result["Nifty_Value"] + result["Gold_Value"]
    result["Absolute_Return_Pct"] = np.where(
        result["Total_Invested"] > 0,
        (result["Portfolio_Value"] - result["Total_Invested"])
        / result["Total_Invested"]
        * 100,
        0.0,
    )
    return result


def rolling_volatility(
    df: pd.DataFrame,
    price_col: str = "Nifty_Close",
    window: int = VOLATILITY_WINDOW,
) -> pd.Series:
    """Annualized 30-day rolling volatility from daily log returns."""
    prices = df.set_index("Date")[price_col]
    log_returns = np.log(prices / prices.shift(1))
    rolling_std = log_returns.rolling(window=window, min_periods=window).std()
    vol = (rolling_std * np.sqrt(252) * 100).rename("Nifty_Volatility_30D")
    return vol.reset_index()


def sentiment_impact(
    df: pd.DataFrame,
    shock_threshold: float = SEVERE_SHOCK_THRESHOLD,
    lag_days: int = SENTIMENT_LAG_DAYS,
    price_col: str = "Nifty_Close",
) -> dict:
    """
    Average % change in Nifty price `lag_days` after a severe negative shock.
    """
    data = df.set_index("Date").copy()
    data["Pct_Change_Forward"] = (
        data[price_col].shift(-lag_days) / data[price_col] - 1
    ) * 100

    shocks = data[data["Sentiment_Score"] < shock_threshold]
    valid = shocks["Pct_Change_Forward"].dropna()

    if len(valid) == 0:
        return {
            "avg_pct_change": np.nan,
            "n_shocks": 0,
            "shock_dates": [],
        }

    return {
        "avg_pct_change": float(valid.mean()),
        "n_shocks": int(len(valid)),
        "shock_dates": shocks.index.strftime("%Y-%m-%d").tolist(),
    }


def run_full_analysis(csv_path: Path = MARKET_CSV) -> dict:
    """Run all analytics and return results for the dashboard."""
    df = load_market_data(csv_path)
    sip_df = calculate_combined_sip(df)
    vol_df = rolling_volatility(df)
    sip_df = sip_df.merge(vol_df, on="Date", how="left")

    impact = sentiment_impact(df)
    latest = sip_df.iloc[-1]

    return {
        "sip_timeseries": sip_df,
        "market": df,
        "sentiment_impact": impact,
        "kpis": {
            "total_invested": float(latest["Total_Invested"]),
            "portfolio_value": float(latest["Portfolio_Value"]),
            "absolute_return_pct": float(latest["Absolute_Return_Pct"]),
            "nifty_price": float(latest["Nifty_Close"]),
        },
    }


if __name__ == "__main__":
    from data_pipeline import export_market_data

    if not MARKET_CSV.exists():
        export_market_data()

    results = run_full_analysis()
    impact = results["sentiment_impact"]
    print(f"SIP rows: {len(results['sip_timeseries'])}")
    print(
        f"Sentiment impact ({impact['n_shocks']} shocks): "
        f"{impact['avg_pct_change']:.2f}% avg over 3 days"
    )
