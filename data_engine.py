import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# --- INSTITUTIONAL TICKER DICTIONARIES ---
MARKET_TICKERS = {
    "Equities": {
        "^GSPC": "S&P 500", "^DJI": "Dow Jones", "^IXIC": "Nasdaq", "^RUT": "Russell 2000",
        "^STOXX50E": "Euro Stoxx 50", "^N225": "Nikkei 225", "^HSI": "Hang Seng", "000001.SS": "Shanghai Comp"
    },
    "FX": {
        "EURUSD=X": "EUR/USD", "JPY=X": "USD/JPY", "GBPUSD=X": "GBP/USD",
        "AUDUSD=X": "AUD/USD", "CNY=X": "USD/CNY", "DX-Y.NYB": "US Dollar Index"
    },
    "Commodities": {
        "CL=F": "WTI Crude", "BZ=F": "Brent Crude", "NG=F": "Natural Gas",
        "GC=F": "Gold", "SI=F": "Silver", "HG=F": "Copper", "ZC=F": "Corn"
    }
}

@st.cache_data(ttl=900)
def fetch_sector_data(sector_name, period="1y"):
    """Fetches data for a specific asset class and returns a styled Tear Sheet matrix."""
    tickers = MARKET_TICKERS[sector_name]
    
    data = yf.download(list(tickers.keys()), period=period, progress=False)['Close']
    
    if isinstance(data, pd.Series):
        data = data.to_frame()
        
    df = data.ffill().sort_index()
    
    matrix = pd.DataFrame({
        'Last Price': df.iloc[-1],
        '1D %': (df.iloc[-1] / df.iloc[-2] - 1) * 100,
        '1W %': (df.iloc[-1] / df.iloc[-6] - 1) * 100 if len(df) >= 6 else np.nan,
        '1M %': (df.iloc[-1] / df.iloc[-22] - 1) * 100 if len(df) >= 22 else np.nan
    })
    
    matrix.rename(index=tickers, inplace=True)
    return matrix.round(2)

@st.cache_data(ttl=3600)
def fetch_yield_curve():
    """Pulls current Treasury yields directly from FRED CSV endpoints (No dependencies)."""
    series_map = {
        "DGS1MO": 1/12, "DGS3MO": 0.25, "DGS6MO": 0.5, "DGS1": 1.0,
        "DGS2": 2.0, "DGS5": 5.0, "DGS10": 10.0, "DGS30": 30.0
    }
    
    curve_data = {
        "Tenor": ["1M", "3M", "6M", "1Y", "2Y", "5Y", "10Y", "30Y"],
        "Years": list(series_map.values()),
        "Yield (%)": []
    }
    
    for series_id in series_map.keys():
        url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
        try:
            df = pd.read_csv(url)
            df = df[df[series_id] != '.'].dropna()
            latest_yield = float(df[series_id].iloc[-1])
            curve_data["Yield (%)"].append(latest_yield)
        except Exception:
            curve_data["Yield (%)"].append(np.nan)
            
    return pd.DataFrame(curve_data)

@st.cache_data(ttl=3600)
def fetch_key_economic_prints():
    """
    Pulls top-level US Macroeconomic indicators via direct FRED CSV scraping, 
    calculates standard metrics, and formats a Tear Sheet.
    """
    macro_series = {
        "A191RL1Q225SBEA": {"name": "Real GDP (QoQ %)", "type": "abs"},
        "CPILFESL": {"name": "Core CPI (MoM %)", "type": "pct"},
        "CPIAUCSL": {"name": "Headline CPI (MoM %)", "type": "pct"},
        "UNRATE": {"name": "Unemployment Rate (%)", "type": "abs"},
        "PAYEMS": {"name": "Non-Farm Payrolls (k)", "type": "diff"},
        "RSAFS": {"name": "Retail Sales (MoM %)", "type": "pct"},
        "FEDFUNDS": {"name": "Effective Fed Funds Rate (%)", "type": "abs"}
    }
    
    records = []
    
    for series_id, meta in macro_series.items():
        url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
        try:
            df = pd.read_csv(url)
            df = df[df[series_id] != '.'].dropna()
            series_data = df[series_id].astype(float)
            
            if len(series_data) < 2:
                continue
                
            latest_val = series_data.iloc[-1]
            prev_val = series_data.iloc[-2]
            
            if meta["type"] == "pct":
                latest_print = ((latest_val / prev_val) - 1) * 100
                prev_print = ((prev_val / series_data.iloc[-3]) - 1) * 100 if len(series_data) > 2 else np.nan
            elif meta["type"] == "diff":
                latest_print = latest_val - prev_val
                prev_print = prev_val - series_data.iloc[-3] if len(series_data) > 2 else np.nan
            else:
                latest_print = latest_val
                prev_print = prev_val
                
            change = latest_print - prev_print
            
            records.append({
                "Indicator": meta["name"],
                "Latest Print": latest_print,
                "Previous Print": prev_print,
                "Change (Net)": change
            })
        except Exception:
            continue
            
    return pd.DataFrame(records).set_index("Indicator")
