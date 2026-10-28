import os
from pathlib import Path

os.chdir(Path(__file__).resolve().parent)

import plotly.graph_objects as go
import pandas as pd
import numpy as np
from itertools import cycle
import plotly.express as px
from datetime import datetime, timedelta
import streamlit as st
import base64
from pathlib import Path
import ast
from localStoragePy import localStoragePy
import storage
import storage_id_cleanup
import prices


CENTRAL_CASE = 20.44
DEFAULT_SIGMA = 45

history, realised_vol, realised_vol_ex_jumps, source = prices.get_history()
last_close = float(history["AdjClose"].iloc[-1])
last_date = history["Date"].iloc[-1].strftime("%d.%m.%Y")
DEFAULT_MU = int(round((CENTRAL_CASE / last_close - 1) * 100))
DEFAULT_SIGMA = int(round(realised_vol * 100))


class SingleLineSimulation:

    def __init__(self, start_price, expected_return, volatility):
        self.start_price = start_price
        self.expected_return = expected_return
        self.volatility = volatility

        self.x_values = np.linspace(0, 12, 253).tolist()

        self.y_values = []

        self.model_output()

    def model_output(self):
        s = self.start_price
        mu = self.expected_return
        sigma = self.volatility
        dt = 1 / 252

        rng = np.random.default_rng(0)
        shocks = rng.standard_normal((300, 252))
        steps = (mu - 0.5 * sigma ** 2) * dt + sigma * np.sqrt(dt) * shocks
        paths = s * np.exp(np.cumsum(steps, axis = 1))
        paths = np.hstack([np.full((300, 1), s), paths])

        self.y_values = np.median(paths, axis = 0).tolist()


class SingleLinePlot:

    def __init__(self, start_price, expected_return, volatility):
        self.data = SingleLineSimulation(start_price, expected_return, volatility)
        self.x_data = self.data.x_values
        self.y_data = self.data.y_values

        y_max = max(max(self.y_data) * 1.1, 25)
        y_min = min(min(self.y_data) * 0.9, 12)

        self.create_figure("", "MAT share price ($)", "Months from today", y_min, y_max)

    def create_figure(self, fig_title, yaxis_title, xaxis_title, y_min, y_max):
        fig = go.Figure().update_layout(template ="plotly_white", title = fig_title, title_x = 0.5, title_y = 0.94, title_font_weight = 600)
        fig.update_layout(autosize = True)
        fig.update_layout(font_family = "Georgia", font_weight = 600, font_size = 18, font_color = "#00274C")
        fig.update_layout(paper_bgcolor = "#FFFFFF")
        fig.update_layout(plot_bgcolor = "#FFFFFF")
        fig.update_yaxes(ticksuffix = " ", tickprefix = "$", title = yaxis_title, title_standoff = 20, range = [y_min, y_max], showgrid = True, showline = False, linecolor = "#FFFFFF", zeroline = False, title_font = dict(size = 20), tickfont = dict(size = 18))
        fig.update_layout(margin=dict(t=45, b=65, l=100, r=0))
        fig.update_xaxes(title = xaxis_title, title_standoff = 20, range = [-0.5, 12], showgrid = True, showline = False, linecolor = "#FFFFFF", zeroline = False, title_font = dict(size = 20), tickfont = dict(size = 18))
        self.plot_data(self.x_data, self.y_data, 3, fig)

    def plot_data(self, x_data, y_data, line_width, fig):

        fig.add_trace(go.Scatter(x = x_data, y = y_data, line = dict(width = line_width, color = "#FFCB05"), opacity = 1, showlegend=False))

        above = [i for i, v in enumerate(y_data) if v >= CENTRAL_CASE]

        if above:
            month = x_data[above[0]]
            text = f"  On median, MAT reaches the central case (${CENTRAL_CASE:.2f}) after {round(month, 1)} months.  "
        else:
            month = 12
            text = f"  On median, MAT ends at ${round(y_data[-1], 2)} after 12 months (central case ${CENTRAL_CASE:.2f}).  "

        position = "top right" if month < 6 else "top left"

        fig.add_vline(x=month, line_width=3, line_dash="dash", line_color="#D9A800", annotation_text = text, annotation_position=position)
        fig.update_annotations(font=dict(size = 13, color = "#00274C"), bgcolor = "rgba(255, 203, 5, 0.25)", borderpad = 4)
        st.plotly_chart(fig, config = {'scrollZoom': False}, theme = None)


def save_to_local_storage(to_save_param):

    for key, value in to_save_param.items():
        localStorage.setItem(key, value)


def load_css(file_name):
    with open(file_name) as f:
        st.html(f"<style>{f.read()}</style>")


def image_to_base64(path):
    return base64.b64encode(Path(path).read_bytes()).decode()


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

    st.html(f"<style>.st-key-overview button {{ background: #FFCB05 !important; border-color: #FFCB05 !important; }} .st-key-overview button p {{ color: #00274C !important; }}</style>")

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

    col1, gap1, col2 = st.columns([1, 0.1, 1])

    if (localStorage.getItem("MU") != None) and (localStorage.getItem("SIGMA") != None):
        ls = int(localStorage.getItem("MU"))
        ms = int(localStorage.getItem("SIGMA"))

    else:
        ls, ms = DEFAULT_MU, DEFAULT_SIGMA


    with col1:
        val1 = st.slider("Expected annual return (%)", -40, 60, ls, key = "left_slider")
        st.markdown(f'<div class="slider-hint">Central case ${CENTRAL_CASE:.2f} from the last close of ${last_close:.2f} ({last_date}, {source}) implies {DEFAULT_MU:+d}%</div>', unsafe_allow_html = True)

    with col2:
        val2 = st.slider("Annual volatility (%)", 10, 80, ms, key = "middle_slider")
        st.markdown(f'<div class="slider-hint">Realised over the last year: {round(realised_vol * 100)}% ({round(realised_vol_ex_jumps * 100)}% without the two biggest daily moves)</div>', unsafe_allow_html = True)


    to_save = {"MU" : val1, "SIGMA" : val2}

    SingleLinePlot(last_close, val1 / 100, val2 / 100)

    st.markdown('<div class="slider-hint">The median of 300 simulated years under the assumptions above. Press Simulate! to see all of them.</div>', unsafe_allow_html = True)

    save_to_local_storage(to_save)


main()
