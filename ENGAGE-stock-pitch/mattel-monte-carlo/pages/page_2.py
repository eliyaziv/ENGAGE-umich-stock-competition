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
from plotly.subplots import make_subplots
from localStoragePy import localStoragePy
import storage
import storage_id_cleanup
import prices


CENTRAL_CASE = 20.44

history, realised_vol, realised_vol_ex_jumps, source = prices.get_history()
last_close = float(history["AdjClose"].iloc[-1])
DEFAULT_MU = int(round((CENTRAL_CASE / last_close - 1) * 100))
DEFAULT_SIGMA = int(round(realised_vol * 100))


class LineSimulation:

    def __init__(self, start_price, expected_return, volatility, rng):
        self.start_price = start_price
        self.expected_return = expected_return
        self.volatility = volatility
        self.rng = rng

        self.x_values = np.linspace(0, 12, 253).tolist()

        self.y_values = []

        self.model_output()


    def model_output(self):
        s = self.start_price
        mu = self.expected_return
        sigma = self.volatility
        dt = 1 / 252

        shocks = self.rng.standard_normal(252)
        steps = (mu - 0.5 * sigma ** 2) * dt + sigma * np.sqrt(dt) * shocks
        path = s * np.exp(np.cumsum(steps))

        self.y_values = [s] + path.tolist()


class LinePlot:

    def __init__(self, start_price, expected_return, volatility):
        rng = np.random.default_rng(0)
        self.data = [LineSimulation(start_price, expected_return, volatility, rng) for i in range(300)]
        self.x_data = [element.x_values for element in self.data]
        self.y_data = [element.y_values for element in self.data]

        self.y_data = np.array(self.y_data)

        self.create_figure("", "MAT share price ($)", "Months from today")

    def get_data(self):
        return self.x_data, self.y_data


    def create_figure(self, fig_title, yaxis_title, xaxis_title):
        fig = go.Figure().update_layout(template ="plotly_white", title = fig_title, title_x = 0.5, title_y = 0.94, title_font_weight = 600)
        fig.update_layout(autosize = True)
        fig.update_layout(font_family = "Georgia", font_weight = 600, font_size = 18)
        fig.update_layout(paper_bgcolor = "#FFFFFF")
        fig.update_layout(plot_bgcolor = "#FFFFFF")
        fig.update_yaxes(ticksuffix = " ", tickprefix = "$", title = yaxis_title, title_standoff = 20, showgrid = True, showline = False, linecolor = "#FFFFFF", zeroline = False, title_font = dict(size = 16), tickfont = dict(size = 14))
        fig.update_layout(margin=dict(t=0, b=95, l=100, r=0))
        fig.update_xaxes(title = xaxis_title, title_standoff = 20.25, range = [-0.5, 12], showgrid = True, showline = False, linecolor = "#FFFFFF", zeroline = False, title_font = dict(size = 16), tickfont = dict(size = 14))
        self.plot_data(self.x_data, self.y_data, 3, fig)

    def find_median_values(self, data):
        median_values = []
        corresp_values = np.dstack(data)
        corresp_values = corresp_values[0]
        for element in corresp_values:
            median_values.append(np.median(element))

        return median_values

    def plot_data(self, x_data, y_data, line_width, fig):
        palette = cycle(px.colors.sequential.RdBu)
        for i in range(len(y_data)):
            fig.add_trace(go.Scatter(x = x_data[i], y = y_data[i], line = dict(width = line_width, color = next(palette)), opacity = 0.15, showlegend=False))
        median_values = self.find_median_values(y_data)

        self.median_values = median_values

        fig.add_trace(go.Scatter(x = x_data[0], y = median_values, line = dict(width = line_width, color = "#8B0000"), opacity = 1, showlegend=False))
        self.fig = fig
        return self.fig


class HistSimulation:

    def __init__(self, months_elapsed, x_data, y_data):
        self.x_data = x_data
        self.y_data = y_data
        self.calculate(months_elapsed)


    def calculate(self, months_elapsed):
        absolute_values = []

        for val in self.x_data[0]:
            absolute_values.append(abs(val-months_elapsed))

        pointer = absolute_values.index(min(absolute_values))

        self.data = np.dstack(self.y_data)[0][pointer]

        return self.data

class HistPlot:

    def __init__(self, month, x_data, y_data):
        Worlddata = HistSimulation(month, x_data, y_data)
        self.values = Worlddata.data

        self.median = np.median(self.values)

        self.create_figure(fig_title = "", yaxis_title = "Frequency", xaxis_title= f"MAT price {month} month(s) from today")

    def create_figure(self, fig_title, yaxis_title, xaxis_title):
        fig = make_subplots(rows = 2, shared_xaxes = True, vertical_spacing = 0.00, row_heights=[0.3,0.7]).update_layout(template ="plotly_white", title = fig_title, title_x = 0.5, title_y = 0.94, title_font_weight = 600)
        fig.update_layout(autosize = True)
        fig.update_layout(font_family = "Georgia", font_weight = 600, font_size = 18)
        fig.update_layout(paper_bgcolor = "#FFFFFF")
        fig.update_layout(plot_bgcolor = "#FFFFFF")
        fig.update_yaxes(ticksuffix = " ", title = yaxis_title, title_standoff = 20, title_font = dict(size = 15), tickfont = dict(size = 14))
        fig.update_layout(margin=dict(t=0, b=95, l=90, r=20), showlegend = False)
        fig.update_xaxes(tickprefix = "$", title = xaxis_title, title_standoff = 18, ticklabelstandoff = 10, title_font = dict(size = 15), row = 2, col = 1, tickfont = dict(size = 14))
        self.plot_data(fig, self.values, self.median)

    def plot_data(self, fig, dataset, median):

        self.median = median

        fig.add_trace(go.Histogram(x = dataset, marker_color = "#00274C"), row = 2, col = 1)
        fig.add_trace(go.Box(x=dataset, marker_color = "#D9A800", line_color = "#D9A800", fillcolor = "rgba(255, 203, 5, 0.45)"), row = 1, col = 1)
        fig.update_yaxes(title_text = None, showticklabels=False, row = 1, col = 1)
        self.fig = fig
        return fig


def load_css(file_name):
    with open(file_name) as f:
        st.html(f"<style>{f.read()}</style>")


def image_to_base64(path):
    return base64.b64encode(Path(path).read_bytes()).decode()


@st.cache_data
def get_line_simulation(start_price, mu, sigma):
    line_plot = LinePlot(start_price, mu, sigma)
    x_data, y_data = line_plot.get_data()
    return x_data, y_data, line_plot.fig


def metric_card(title, value, subtitle=None):
    subtitle_html = f'<div class="metric-card-subtitle">{subtitle}</div>' if subtitle else ""

    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-card-title">{title}</div>
            <div class="metric-card-number">{value}</div>
            {subtitle_html}
        </div>
        """,
        unsafe_allow_html=True
    )


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

    st.html(f"<style>.st-key-simulation button {{ background: #FFCB05 !important; border-color: #FFCB05 !important; }} .st-key-simulation button p {{ color: #00274C !important; }}</style>")

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

    if (localStorage.getItem("MU") != None) and (localStorage.getItem("SIGMA") != None):
        mu = int(localStorage.getItem("MU"))
        sigma = int(localStorage.getItem("SIGMA"))
    else:
        mu, sigma = DEFAULT_MU, DEFAULT_SIGMA

    x_data, y_data, line_fig = get_line_simulation(last_close, mu / 100, sigma / 100)

    with st.container(key="metric_slider_row"):
        left_col, slider_col, right_col = st.columns(
            [1, 2.2, 1],
            gap="medium",
            vertical_alignment="center"
        )


    if localStorage.getItem("slider_pos") == None:
        slider_position = 6
    else:
        slider_position = int(localStorage.getItem("slider_pos"))

    try:
        slider_position = st.session_state["month_slider"]
    except KeyError:
        pass


    hist_fig = HistPlot(slider_position, x_data, y_data)

    hist_median = hist_fig.median
    hist_values = hist_fig.values

    hist_fig = hist_fig.fig

    above_today = np.mean(hist_values > last_close)
    final_prices = y_data[:, -1]
    above_central = np.mean(final_prices >= CENTRAL_CASE)


    with st.container(key = "wide_chart_section"):
        col1, col2 = st.columns(2, gap="small", vertical_alignment="center")

        with col1:
            st.plotly_chart(line_fig, width="stretch", config={"scrollZoom": False}, theme = None)

        with col2:
            st.plotly_chart(hist_fig, width="stretch", config={"scrollZoom": False}, theme = None)


    with slider_col:
            slider_position = st.slider(
                "Please select a month to inspect",
                1, 12, slider_position, step = 1,
                key="month_slider"
            )

    localStorage.setItem("slider_pos", int(slider_position))

    with left_col:
        line_metric = metric_card("Metric", f"${round(hist_median, 2):.2f}", f"On median, MAT trades at ${round(hist_median, 2):.2f} {slider_position} month(s) from today, with {round(above_today * 100)}% of simulated years above today's ${last_close:.2f}.")


    with right_col:
        hist_metric = metric_card("Metric", f"{round(above_central * 100)}%", f"of the 300 simulated years end at or above the central case (${CENTRAL_CASE:.2f}) after 12 months.")

main()
