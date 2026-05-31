import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import pandas_datareader as pdr
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

@st.cache_data(ttl=900) # Cache for 15 minutes to respect API rate limits
def fetch_sector_data(sector_name, period="1y"):
    """Fetches data for a specific asset class and returns a styled Tear Sheet matrix."""
    tickers = MARKET_TICKERS[sector_name]
    
    # Download data silently
    data = yf.download(list(tickers.keys()), period=period, progress=False)['Close']
    
    # Handle single-ticker edge cases (yfinance returns a Series instead of DataFrame)
    if isinstance(data, pd.Series):
        data = data.to_frame()
        
    # Forward fill missing data (e.g., holidays in different countries)
    df = data.ffill().sort_index()
    
    # Calculate Momentum Matrix
    matrix = pd.DataFrame({
        'Last Price': df.iloc[-1],
        '1D %': (df.iloc[-1] / df.iloc[-2] - 1) * 100,
        '1W %': (df.iloc[-1] / df.iloc[-6] - 1) * 100 if len(df) >= 6 else np.nan,
        '1M %': (df.iloc[-1] / df.iloc[-22] - 1) * 100 if len(df) >= 22 else np.nan
    })
    
    # Rename index to readable names
    matrix.rename(index=tickers, inplace=True)
    return matrix.round(2)

@st.cache_data(ttl=3600)
def fetch_yield_curve():
    """Pulls current Treasury yields from FRED to construct the curve."""
    # FRED Series IDs for constant maturity treasuries
    series_map = {
        "DGS1MO": 1/12, "DGS3MO": 0.25, "DGS6MO": 0.5, "DGS1": 1.0,
        "DGS2": 2.0, "DGS5": 5.0, "DGS10": 10.0, "DGS30": 30.0
    }
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=14) # Pull last two weeks to ensure we get the latest close
    
    df = pdr.get_data_fred(list(series_map.keys()), start=start_date, end=end_date)
    latest_yields = df.ffill().iloc[-1] # Get most recent valid row
    
    # Structure for plotting
    curve_data = pd.DataFrame({
        "Tenor": ["1M", "3M", "6M", "1Y", "2Y", "5Y", "10Y", "30Y"],
        "Years": list(series_map.values()),
        "Yield (%)": latest_yields.values
    })
    
    return curve_data
    
@st.cache_data(ttl=3600)
def fetch_key_economic_prints():
    """
    Pulls top-level US Macroeconomic indicators from FRED, calculates the 
    standard Wall Street metrics (MoM, QoQ, or absolute change), and formats a Tear Sheet.
    """
    # Map FRED Series IDs to readable names and their calculation types
    # Types: 'abs' (Absolute Level), 'diff' (Absolute Change), 'pct' (Percent Change)
    macro_series = {
        "A191RL1Q225SBEA": {"name": "Real GDP (QoQ %)", "type": "abs"}, # Already a % change
        "CPILFESL": {"name": "Core CPI (MoM %)", "type": "pct"},
        "CPIAUCSL": {"name": "Headline CPI (MoM %)", "type": "pct"},
        "UNRATE": {"name": "Unemployment Rate (%)", "type": "abs"},
        "PAYEMS": {"name": "Non-Farm Payrolls (k)", "type": "diff"},
        "RSAFS": {"name": "Retail Sales (MoM %)", "type": "pct"},
        "FEDFUNDS": {"name": "Effective Fed Funds Rate (%)", "type": "abs"}
    }
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=180) # 6 months is enough for latest vs previous
    
    try:
        # Fetch all series from FRED
        df = pdr.get_data_fred(list(macro_series.keys()), start=start_date, end=end_date)
        df = df.ffill() # Forward fill to align dates
        
        records = []
        for series_id, meta in macro_series.items():
            series_data = df[series_id].dropna()
            if len(series_data) < 2:
                continue
                
            latest_val = series_data.iloc[-1]
            prev_val = series_data.iloc[-2]
            
            # Calculate the metric based on institutional standard
            if meta["type"] == "pct":
                latest_print = ((latest_val / prev_val) - 1) * 100
                prev_print = ((prev_val / series_data.iloc[-3]) - 1) * 100 if len(series_data) > 2 else np.nan
            elif meta["type"] == "diff":
                latest_print = latest_val - prev_val
                prev_print = prev_val - series_data.iloc[-3] if len(series_data) > 2 else np.nan
            else: # "abs"
                latest_print = latest_val
                prev_print = prev_val
                
            change = latest_print - prev_print
            
            records.append({
                "Indicator": meta["name"],
                "Latest Print": latest_print,
                "Previous Print": prev_print,
                "Change (Net)": change
            })
            
        return pd.DataFrame(records).set_index("Indicator")
    except Exception as e:
        st.error(f"Macro Data Pipeline Error: {e}")
        return pd.DataFrame()
