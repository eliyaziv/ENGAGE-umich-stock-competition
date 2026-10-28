import os
from pathlib import Path

os.chdir(Path(__file__).resolve().parent.parent)

import streamlit as st
import base64
from pathlib import Path
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
from localStoragePy import localStoragePy
import storage
import storage_id_cleanup
import prices


CENTRAL_CASE = 20.44

history, realised_vol, realised_vol_ex_jumps, source = prices.get_history()
last_close = float(history["AdjClose"].iloc[-1])
last_date = history["Date"].iloc[-1].strftime("%d.%m.%Y")
DEFAULT_MU = int(round((CENTRAL_CASE / last_close - 1) * 100))
DEFAULT_SIGMA = int(round(realised_vol * 100))


def load_css(file_name):
    with open(file_name) as f:
        st.html(f"<style>{f.read()}</style>")


def image_to_base64(path):
    return base64.b64encode(Path(path).read_bytes()).decode()


def money(v):
    for unit, div in (("T", 1e12), ("B", 1e9), ("M", 1e6)):
        if abs(v) >= div:
            return f"${v / div:.2f}{unit}"
    return f"${v:,.0f}"


def count(v):
    for unit, div in (("B", 1e9), ("M", 1e6), ("K", 1e3)):
        if abs(v) >= div:
            return f"{v / div:.1f}{unit}"
    return f"{v:,.0f}"


def fact_card(label, value, sub = ""):
    return f'<div class="fact"><div class="label">{label}</div><div class="value">{value}</div><div class="sub">{sub}</div></div>'


class HistoryPlot:

    def __init__(self, history):
        self.dates = history["Date"]
        self.closes = history["AdjClose"]
        self.high_date = history.loc[history["AdjClose"].idxmax(), "Date"]
        self.low_date = history.loc[history["AdjClose"].idxmin(), "Date"]
        changes = history["AdjClose"].pct_change()
        big = changes.abs().idxmax()
        self.big_date = history.loc[big, "Date"]
        self.big_move = changes.loc[big] * 100

        self.create_figure("", "MAT share price ($)", "Last 12 months")

    def create_figure(self, fig_title, yaxis_title, xaxis_title):
        fig = go.Figure().update_layout(template ="plotly_white", title = fig_title, autosize = True, height = 420)
        fig.update_layout(font_family = "Georgia", font_weight = 600, font_size = 18, font_color = "#00274C")
        fig.update_layout(paper_bgcolor = "#FFFFFF")
        fig.update_layout(plot_bgcolor = "#FFFFFF")
        fig.update_yaxes(ticksuffix = " ", tickprefix = "$", title = yaxis_title, title_standoff = 20, showgrid = True, showline = False, linecolor = "#FFFFFF", zeroline = False, title_font = dict(size = 20), tickfont = dict(size = 18))
        fig.update_layout(margin=dict(t=45, b=65, l=100, r=0))
        fig.update_xaxes(title = xaxis_title, title_standoff = 20, showgrid = True, showline = False, linecolor = "#FFFFFF", zeroline = False, title_font = dict(size = 20), tickfont = dict(size = 16), tickformat = "%b %y")
        self.plot_data(fig)

    def plot_data(self, fig):
        hi = float(self.closes.max())
        lo = float(self.closes.min())

        fig.add_trace(go.Scatter(x = self.dates, y = self.closes, line = dict(width = 3, color = "#00274C"), fill = "tozeroy", fillcolor = "rgba(255, 203, 5, 0.18)", showlegend = False,
                                 customdata = self.dates.dt.strftime("%d.%m.%Y"), hovertemplate = "%{customdata}: $%{y:.2f}<extra></extra>"))

        marker = dict(size = 13, color = "#FFCB05", line = dict(width = 2.5, color = "#00274C"))
        fig.add_trace(go.Scatter(x = [self.high_date], y = [hi], mode = "markers+text", marker = marker, text = [f"52-week high ${hi:.2f}"], textposition = "top center", textfont = dict(size = 13, color = "#00274C"), showlegend = False, hoverinfo = "skip"))
        fig.add_trace(go.Scatter(x = [self.low_date], y = [lo], mode = "markers+text", marker = marker, text = [f"52-week low ${lo:.2f}"], textposition = "bottom center", textfont = dict(size = 13, color = "#00274C"), showlegend = False, hoverinfo = "skip"))

        fig.add_vline(x = self.big_date, line_width = 2, line_dash = "dash", line_color = "#D9A800", annotation_text = f"  Biggest daily move: {self.big_move:+.0f}% on {self.big_date.strftime('%d.%m.%Y')}  ", annotation_position = "top left")
        fig.update_annotations(font = dict(size = 13, color = "#00274C"), bgcolor = "rgba(255, 203, 5, 0.25)", borderpad = 4)
        fig.update_yaxes(range = [lo * 0.85, hi * 1.12])

        st.plotly_chart(fig, config = {'scrollZoom': False}, theme = None)


def main():

    with open("last_cleanup.txt", "r+") as f:
        content = f.readline().strip()
        if not content:
            f.seek(0)
            f.write(str(datetime.now().isoformat()))
            f.truncate()


    with open("last_cleanup.txt", "r") as f:
        last_cleanup_time = datetime.fromisoformat(f.read().strip())

    if datetime.now() - last_cleanup_time >= timedelta(minutes=120):
        storage_id_cleanup.main()


    global localStorage


    if "user_storage_id" not in st.session_state:
        user_storage_id = storage.create_storage_id()
        st.session_state["user_storage_id"] = user_storage_id
    else:
        user_storage_id = st.session_state["user_storage_id"]


    localStorage = localStoragePy(f'my_app_{user_storage_id}.py')

    st.set_page_config(layout="wide", page_title = "MAT Monte Carlo")

    load_css("styles.css")

    st.markdown(
        """
        <div id="mobile-blocker">
            <div class="mobile-blocker-card">
                <h1>Desktop required</h1>
                <p>This website is optimized for laptop and desktop screens.</p>
                <p>Please open it on a larger display.</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True)

    st.markdown(
        f"""
        <div class="brand-header">
            <img src="data:image/png;base64,{image_to_base64("static/michigan-seal.png")}">
            <div>
                <div class="brand-title">Mattel, Inc. (MAT): Monte Carlo stress test of the target price</div>
                <div class="brand-sub">Stock pitch submission to the ENGAGE® Undergraduate Investment Conference, University of Michigan, Ann Arbor, 14.11.2026</div>
                <div class="brand-bar"></div>
            </div>
            <img src="data:image/png;base64,{image_to_base64("static/uic-logo.png")}">
        </div>
        """,
        unsafe_allow_html = True)

    st.html(f"<style>.st-key-information button {{ background: #FFCB05 !important; border-color: #FFCB05 !important; }} .st-key-information button p {{ color: #00274C !important; }}</style>")

    with st.container(horizontal=True, horizontal_alignment="center", gap="small", key="nav_row"):

        if st.button("Information", key="information"):
            localStorage.setItem("page_switch", True)
            st.switch_page("pages/page_0.py")

        if st.button("Overview", key="overview"):
            localStorage.setItem("page_switch", True)
            st.switch_page("streamlit_app.py")

        if st.button("Model description", key="model_description"):
            localStorage.setItem("page_switch", True)
            st.switch_page("pages/page_1.py")

        if st.button("Simulate!", key="simulation"):
            localStorage.setItem("page_switch", True)
            st.switch_page("pages/page_2.py")

        if st.button("Reset", key = "reset"):
            st.session_state["left_slider"] = DEFAULT_MU
            st.session_state["middle_slider"] = DEFAULT_SIGMA
            st.session_state["month_slider"] = 6

            st.cache_data.clear()
            localStorage.clear()
            st.switch_page("streamlit_app.py")

    st.divider()

    quote = prices.get_quote(history)

    prev_close = float(history["AdjClose"].iloc[-2])
    change = last_close - prev_close
    sign = "+" if change >= 0 else ""
    cls = "up" if change >= 0 else "down"

    cards = [fact_card("Last price", f"${last_close:.2f}", f'<span class="{cls}">{sign}{change:.2f} ({sign}{change / prev_close * 100:.2f}%)</span>')]

    if quote["marketCap"]:
        cards.append(fact_card("Market cap", money(quote["marketCap"])))
    if quote["averageVolume"]:
        cards.append(fact_card("Avg. daily volume", count(quote["averageVolume"]), "last 3 months"))
    if quote["shortPercentOfFloat"] is not None:
        cards.append(fact_card("Short interest", f"{quote['shortPercentOfFloat'] * 100:.1f}%", "of float"))
    if quote["earnings_date"] and pd.Timestamp(quote["earnings_date"]) >= pd.Timestamp(datetime.now().date()):
        cards.append(fact_card("Next earnings", pd.Timestamp(quote["earnings_date"]).strftime("%d.%m.%Y")))

    details = "Yahoo Finance" if quote["live"] else "saved company profile"

    st.markdown('<div class="fact-row">' + "".join(cards) + '</div>' + f'<div class="fact-source">Price as of {last_date}, {source}. Company details: {details}.</div>', unsafe_allow_html = True)

    bits = []
    if quote["sector"]:
        bits.append(f"<b>Sector</b> {quote['sector']}")
    if quote["industry"]:
        bits.append(f"<b>Industry</b> {quote['industry']}")
    hq = ", ".join(x for x in (quote["city"], quote["state"], quote["country"]) if x)
    if hq:
        bits.append(f"<b>Headquarters</b> {hq}")
    if quote["fullTimeEmployees"]:
        bits.append(f"<b>Employees</b> {quote['fullTimeEmployees']:,}")
    if quote["website"]:
        site = quote["website"].replace("https://", "").replace("http://", "").rstrip("/")
        bits.append(f'<b>Website</b> <a href="{quote["website"]}" target="_blank">{site}</a>')

    if bits:
        st.markdown('<div class="profile-line">' + " &nbsp;·&nbsp; ".join(bits) + '</div>', unsafe_allow_html = True)

    if quote["longBusinessSummary"]:
        with st.expander(f"About {quote['longName'] or 'Mattel, Inc.'}"):
            st.markdown(f'<div class="profile-text">{quote["longBusinessSummary"]}</div>', unsafe_allow_html = True)

    HistoryPlot(history)

main()
