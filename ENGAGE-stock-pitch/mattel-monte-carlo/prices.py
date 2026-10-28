import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf


TICKER = "MAT"
PRICE_FILE = "data/mat-prices.csv"


@st.cache_data(ttl = 3600)
def get_history():

    try:
        raw = yf.download(TICKER, period = "1y", interval = "1d", auto_adjust = True, progress = False)
        if raw is None or len(raw) < 120:
            raise ValueError("no data")
        close = raw["Close"]
        if isinstance(close, pd.DataFrame):
            close = close.iloc[:, 0]
        df = pd.DataFrame({"Date": pd.to_datetime(close.index).tz_localize(None), "AdjClose": close.values}).dropna()
        df = df.sort_values("Date").reset_index(drop = True)
        df["AdjClose"] = df["AdjClose"].round(2)
        df.to_csv(PRICE_FILE, index = False, date_format = "%Y-%m-%d")
        source = "Yahoo Finance"

    except Exception:
        df = pd.read_csv(PRICE_FILE, parse_dates = ["Date"]).sort_values("Date").reset_index(drop = True)
        source = "saved file"

    log_returns = np.log(df["AdjClose"]).diff().dropna()
    vol = float(log_returns.std() * np.sqrt(252))
    vol_ex_jumps = float(log_returns[log_returns.abs() <= 0.10].std() * np.sqrt(252))

    return df, vol, vol_ex_jumps, source


@st.cache_data(ttl = 3600)
def get_quote():

    keys = ["marketCap", "beta", "averageVolume", "shortPercentOfFloat", "sector", "industry",
            "city", "state", "country", "fullTimeEmployees", "website", "longBusinessSummary", "longName"]
    out = {k: None for k in keys}
    out["earnings_date"] = None

    try:
        t = yf.Ticker(TICKER)
        info = t.info
        for k in keys:
            out[k] = info.get(k)
        cal = t.calendar
        if isinstance(cal, dict) and cal.get("Earnings Date"):
            out["earnings_date"] = pd.Timestamp(cal["Earnings Date"][0]).strftime("%d.%m.%Y")
    except Exception:
        pass

    return out
