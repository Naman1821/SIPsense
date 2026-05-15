"""
SIPsense — Market Sentiment & SIP Analytics Dashboard
"""

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from analysis_engine import MARKET_CSV, run_full_analysis, SEVERE_SHOCK_THRESHOLD
from data_pipeline import export_market_data

DATA_DIR = Path(__file__).resolve().parent

# Dark theme CSS
st.set_page_config(
    page_title="SIPsense | SIP & Sentiment Analytics",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
    .stApp { background-color: #0e1117; color: #fafafa; }
    div[data-testid="stMetric"] {
        background: linear-gradient(145deg, #1a1f2e 0%, #12151c 100%);
        border: 1px solid #2d3548;
        border-radius: 12px;
        padding: 16px 20px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.35);
    }
    div[data-testid="stMetric"] label { color: #94a3b8 !important; font-size: 0.85rem; }
    div[data-testid="stMetric"] [data-testid="stMetricValue"] { color: #f8fafc !important; }
    h1 { color: #f1f5f9 !important; font-weight: 700 !important; }
    .subtitle { color: #64748b; font-size: 1rem; margin-bottom: 1.5rem; }
  .insight-box {
        background: #1a1f2e;
        border-left: 4px solid #ef4444;
        padding: 1rem 1.25rem;
        border-radius: 0 8px 8px 0;
        margin: 1rem 0;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(ttl=3600)
def load_analytics():
    if not MARKET_CSV.exists():
        export_market_data()
    return run_full_analysis()


def format_inr(value: float) -> str:
    return f"₹{value:,.0f}"


def portfolio_growth_chart(sip_df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=sip_df["Date"],
            y=sip_df["Portfolio_Value"],
            mode="lines",
            name="Portfolio Value",
            line=dict(color="#22d3ee", width=2.5),
            fill="tozeroy",
            fillcolor="rgba(34, 211, 238, 0.08)",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=sip_df["Date"],
            y=sip_df["Total_Invested"],
            mode="lines",
            name="Total Invested",
            line=dict(color="#94a3b8", width=2, dash="dot"),
        )
    )
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#0e1117",
        plot_bgcolor="#12151c",
        height=420,
        margin=dict(l=50, r=30, t=40, b=50),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        xaxis_title="Date",
        yaxis_title="Amount (INR)",
        title=dict(text="SIP Portfolio Growth (5 Years)", font=dict(size=16)),
    )
    return fig


def nifty_sentiment_chart(market_df: pd.DataFrame) -> go.Figure:
    shocks = market_df[market_df["Sentiment_Score"] < SEVERE_SHOCK_THRESHOLD]
    colors = [
        "#ef4444" if s < SEVERE_SHOCK_THRESHOLD else "#6366f1"
        for s in market_df["Sentiment_Score"]
    ]

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(
        go.Scatter(
            x=market_df["Date"],
            y=market_df["Nifty_Close"],
            name="Nifty 50",
            line=dict(color="#fbbf24", width=2),
        ),
        secondary_y=False,
    )

    fig.add_trace(
        go.Bar(
            x=market_df["Date"],
            y=market_df["Sentiment_Score"],
            name="Sentiment",
            marker_color=colors,
            opacity=0.65,
        ),
        secondary_y=True,
    )

    if not shocks.empty:
        fig.add_trace(
            go.Scatter(
                x=shocks["Date"],
                y=shocks["Nifty_Close"],
                mode="markers",
                name="Severe Shock",
                marker=dict(color="#ef4444", size=10, symbol="x", line=dict(width=2)),
            ),
            secondary_y=False,
        )

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#0e1117",
        plot_bgcolor="#12151c",
        height=440,
        margin=dict(l=50, r=50, t=40, b=50),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        title=dict(text="Nifty 50 vs Daily Sentiment (Shocks in Red)", font=dict(size=16)),
        barmode="overlay",
    )
    fig.update_yaxes(title_text="Nifty Close", secondary_y=False)
    fig.update_yaxes(title_text="Sentiment Score", range=[-1.05, 1.05], secondary_y=True)
    return fig


SIP_LOGIC_SNIPPET = '''
# Core SIP compounding logic (monthly ₹5,000 per asset)
units = 0.0
total_invested = 0.0

for date, row in price_data.iterrows():
    if date in first_trading_days_each_month:
        price = row["Nifty_Close"]  # or Gold_Close
        units += 5_000 / price
        total_invested += 5_000

    portfolio_value = units * row["Nifty_Close"]

# Combined portfolio = Nifty value + Gold value
'''


def main():
    st.title("SIPsense")
    st.markdown(
        '<p class="subtitle">Market Sentiment & SIP Analytics — Nifty 50 & Gold</p>',
        unsafe_allow_html=True,
    )

    if st.sidebar.button("Refresh market data"):
        export_market_data()
        load_analytics.clear()

    with st.spinner("Loading market data & analytics..."):
        results = load_analytics()

    kpis = results["kpis"]
    sip_df = results["sip_timeseries"]
    market_df = results["market"]
    impact = results["sentiment_impact"]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total SIP Invested", format_inr(kpis["total_invested"]))
    c2.metric("Current Portfolio Value", format_inr(kpis["portfolio_value"]))
    c3.metric("Absolute Return", f"{kpis['absolute_return_pct']:.2f}%")
    c4.metric("Current Nifty 50", f"{kpis['nifty_price']:,.2f}")

    st.plotly_chart(portfolio_growth_chart(sip_df), use_container_width=True)
    st.plotly_chart(nifty_sentiment_chart(market_df), use_container_width=True)

    st.subheader("Insights")
    avg_chg = impact["avg_pct_change"]
    n_shocks = impact["n_shocks"]

    if pd.notna(avg_chg) and n_shocks > 0:
        direction = "drops" if avg_chg < 0 else "rises"
        st.markdown(
            f"""
            <div class="insight-box">
            <strong>Sentiment Impact:</strong> After <em>severe negative</em> sentiment
            (score &lt; {SEVERE_SHOCK_THRESHOLD}), Nifty 50 <strong>{direction}</strong> by
            <strong>{abs(avg_chg):.2f}%</strong> on average over the next 3 trading days
            (based on {n_shocks} shock events).
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.info("Insufficient severe shock events to compute sentiment impact.")

    vol_latest = sip_df["Nifty_Volatility_30D"].dropna()
    if not vol_latest.empty:
        st.metric(
            "30-Day Rolling Volatility (Nifty, annualized)",
            f"{vol_latest.iloc[-1]:.2f}%",
        )

    with st.expander("Sample Logic (SIP Math)"):
        st.code(SIP_LOGIC_SNIPPET, language="python")
        st.caption(
            "Full implementation: `analysis_engine.calculate_sip()` and "
            "`calculate_combined_sip()`"
        )


if __name__ == "__main__":
    main()
