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

    st.html(f"<style>.st-key-model_description button {{ background: #FFCB05 !important; border-color: #FFCB05 !important; }} .st-key-model_description button p {{ color: #00274C !important; }}</style>")

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

    with st.container(key = "formula"):
        st.latex(r"""
\begin{aligned}
S_{t+1} &= S_t \cdot \exp\!\left( \left(\mu - \tfrac{1}{2}\sigma^{2}\right)\Delta t + \sigma\sqrt{\Delta t}\,Z_t \right), \qquad Z_t \sim \mathcal{N}(0,1) \\
t &= 0, 1, \dots, 252 \qquad \Delta t = \tfrac{1}{252}
\end{aligned}
""")

    col1, gap1, col2, = st.columns([1, 0.05, 1], vertical_alignment="center")

    with col1:
        with st.container(key="parameter_exp"):
            st.markdown(
        f"""
        <ul class="parameter-list">
            <li>S<sub>t</sub> is MAT's share price on trading day t. S<sub>0</sub> is the last close,<br>
                ${last_close:.2f} on {last_date}.</li>
            <li>μ is the expected annual return, the drift the share is assumed to have on average.</li>
            <li>σ is the annual volatility, the size of the daily surprises.</li>
            <li>Δt is one step, a single trading day, so 1/252 of a year.</li>
            <li>Z<sub>t</sub> is a random number drawn from a standard normal distribution, new for every day and for every simulated year.</li>
            <li>−½σ² is a correction so that the average outcome grows at μ even though the moves compound.</li>
            <li>One run of 252 steps is one possible year. The model runs 300 of them.</li>
        </ul>
        """,
        unsafe_allow_html=True
    )


    with col2:
        with st.container(key="model_exp"):
            st.markdown(
            f'''
            The model supports the risk section of the report. Rather than committing to a single number for where MAT will trade, it treats the share price as a random walk:
            every trading day the price moves by a small expected drift (μ) plus a random shock whose size is set by the volatility (σ), which is the standard Geometric Brownian Motion
            used in option pricing. Running the walk for 252 days gives one possible year for the share, and running 300 such years gives the fan of paths on the 'Simulate!' page.
            The yellow line on the 'Overview' page is the median of those years, and the histogram shows where the 300 years put the price in any month you pick.
            Volatility is calibrated to MAT's own closes over the last twelve months ({round(realised_vol * 100)}%, or about {round(realised_vol_ex_jumps * 100)}% if the two biggest one-day moves are left out),
            and the default drift is the one that carries the last close to the central case of the thesis (${CENTRAL_CASE:.2f}) within 12 months.
            The point is not to forecast the price but to show how wide the range of outcomes is even if the thesis is right, and how often the central case is reached along the way. <br>

            *To interact with the model, you may alter μ and σ on the 'Overview' page. These changes will then be reflected after clicking 'Simulate!' in the top ribbon. To restore the calibrated
            defaults, press 'Reset'.*

            ''', unsafe_allow_html = True)

main()
