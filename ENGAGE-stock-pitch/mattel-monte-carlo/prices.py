import json
from pathlib import Path
import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf


TICKER = "MAT"
PRICE_FILE = Path(__file__).resolve().parent / "data/mat-prices.csv"
PROFILE_FILE = Path(__file__).resolve().parent / "data/mat-profile.json"
PRICE_FILE.parent.mkdir(parents=True, exist_ok=True)
PROFILE_KEYS = ["longName", "sector", "industry", "city", "state", "country", "fullTimeEmployees", "website", "longBusinessSummary", "sharesOutstanding"]


def series(raw, column):
    values = raw[column]
    if isinstance(values, pd.DataFrame):
        values = values.iloc[:, 0]
    return values


@st.cache_data(ttl = 3600)
def get_history():

    try:
        raw = yf.download(TICKER, period = "1y", interval = "1d", auto_adjust = True, progress = False)
        if raw is None or len(raw) < 120:
            raise ValueError("no data")
        close = series(raw, "Close")
        volume = series(raw, "Volume")
        df = pd.DataFrame({"Date": pd.to_datetime(close.index).tz_localize(None), "AdjClose": close.values, "Volume": volume.values}).dropna()
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


@st.cache_data(ttl = 600)
def fetch_info():
    try:
        info = yf.Ticker(TICKER).info
        if info and (info.get("sector") or info.get("marketCap")):
            return info
    except Exception:
        pass
    return None


@st.cache_data(ttl = 600)
def fetch_earnings_date():
    try:
        cal = yf.Ticker(TICKER).calendar
        if isinstance(cal, dict) and cal.get("Earnings Date"):
            return pd.Timestamp(cal["Earnings Date"][0]).strftime("%Y-%m-%d")
    except Exception:
        pass
    return None


@st.cache_data(ttl = 600)
def fetch_market_cap():
    try:
        cap = yf.Ticker(TICKER).fast_info["marketCap"]
        if cap:
            return float(cap)
    except Exception:
        pass
    return None


def get_quote(history):

    with open(PROFILE_FILE) as f:
        saved = json.load(f)

    last_close = float(history["AdjClose"].iloc[-1])

    quote = {k: saved.get(k) for k in PROFILE_KEYS}
    quote["earnings_date"] = saved.get("earnings_date")
    quote["marketCap"] = None
    quote["shortPercentOfFloat"] = None
    quote["averageVolume"] = None
    quote["live"] = False

    info = fetch_info()
    if info:
        quote["live"] = True
        for k in PROFILE_KEYS + ["marketCap", "shortPercentOfFloat", "averageVolume"]:
            if info.get(k) is not None:
                quote[k] = info[k]
        try:
            with open(PROFILE_FILE, "w") as f:
                json.dump({**saved, **{k: quote[k] for k in PROFILE_KEYS}}, f, indent = 2, ensure_ascii = False)
        except OSError:
            pass

    earnings = fetch_earnings_date()
    if earnings:
        quote["earnings_date"] = earnings

    if quote["marketCap"] is None:
        quote["marketCap"] = fetch_market_cap()
    if quote["marketCap"] is None and quote["sharesOutstanding"]:
        quote["marketCap"] = quote["sharesOutstanding"] * last_close

    if "Volume" in history.columns and history["Volume"].notna().sum() >= 63:
        quote["averageVolume"] = float(history["Volume"].tail(63).mean())

    return quote
