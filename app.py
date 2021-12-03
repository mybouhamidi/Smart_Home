from json.decoder import JSONDecodeError
import dash
import redis
from datetime import datetime
from flask_caching import Cache
import dash_bootstrap_components as dbc
from dash import html, dcc
from dash_extensions.enrich import Input, Output
from dash_extensions import Download
from dash.exceptions import PreventUpdate
import pandas as pd
import secret

import json
import sys
import os


def find_data_file(filename):
    if getattr(sys, "frozen", False):
        datadir = os.path.dirname(sys.executable)
    else:
        datadir = os.path.dirname(__file__)

    return os.path.join(datadir, filename)


redis = redis.Redis(
    host=secret.host,
    port=secret.port,
    password=secret.password,
)

app = dash.Dash(
    __name__,
    title="Smart Home",
    update_title=None,
    assets_folder=find_data_file("assets/"),
    external_stylesheets=[dbc.themes.GRID],
    suppress_callback_exceptions=True,
    meta_tags=[
        {"name": "viewport", "content": "width=device-width, initial-scale=1"},
    ],
)

cache = Cache(
    app.server, config={"CACHE_TYPE": "filesystem", "CACHE_DIR": "cache-directory"}
)
server = app.server

cache.set("data", {})

TIMEOUT = 1


@cache.memoize(timeout=TIMEOUT)
def call_redis():
    data = redis.get("data").decode()
    data = data.split(";")
    data.pop()
    data_ = []
    for _ in data:
        try:
            data_.append(json.loads(_))
        except JSONDecodeError:
            pass

    df = {"Time": [], "Temperature": [], "Humidity": [], "CO2": []}
    for key in data_:
        df["Time"].append(datetime.fromtimestamp(key["Time"]))
        df["Temperature"].append(key["Temperature"])
        df["Humidity"].append(key["Humidity"])
        df["CO2"].append(key["CO2"])

    return pd.DataFrame(df, columns=["Time", "Temperature", "Humidity", "CO2"])


def get_cache():
    return call_redis()


app.layout = html.Div(
    [
        html.Header(
            className="flex-display row",
            children=[
                html.Div(
                    id="header",
                    children=[
                        html.H1("Air DAQ"),
                        html.P("Monitor your house from anywhere"),
                    ],
                ),
            ],
        ),
        html.Div(
            [
                html.Div(
                    id="display",
                    children=[
                        dbc.Row(
                            [
                                dbc.Col(
                                    html.Div(
                                        id="sensors",
                                        children=[
                                            html.Div(
                                                [
                                                    html.H4(
                                                        "Sensors readings:", id="title"
                                                    ),
                                                    html.Div(id="update_titles"),
                                                ]
                                            ),
                                            dbc.Button(
                                                "Export Data",
                                                id="download-button",
                                                color="primary",
                                                className="mb-3",
                                                n_clicks=0,
                                            ),
                                            Download(id="download_plot"),
                                            dbc.Button(
                                                "Stop/ Resume",
                                                id="stop-button",
                                                color="primary",
                                                className="mb-3",
                                                n_clicks=0,
                                            ),
                                        ],
                                    ),
                                    width=3,
                                ),
                                dbc.Col(
                                    html.Div(
                                        [
                                            dbc.Row(
                                                id="dropdown",
                                                children=[
                                                    dcc.Dropdown(
                                                        id="data-select",
                                                        multi=True,
                                                        style={
                                                            "width": "100%",
                                                            "color": "#000",
                                                        },
                                                        options=[
                                                            {
                                                                "label": "Temperature",
                                                                "value": "Temperature",
                                                            },
                                                            {
                                                                "label": "Humidity",
                                                                "value": "Humidity",
                                                            },
                                                            {
                                                                "label": "CO2 level",
                                                                "value": "CO2",
                                                            },
                                                        ],
                                                    ),
                                                ],
                                            ),
                                            html.Br(),
                                            dbc.Row(
                                                [
                                                    dcc.Graph(
                                                        id="graph",
                                                        responsive=True,
                                                        config={
                                                            "displaylogo": False,
                                                        },
                                                        style={"width": "100%"},
                                                    ),
                                                    dcc.Interval(
                                                        id="int",
                                                        interval=1000,
                                                        n_intervals=0,
                                                    ),
                                                    html.Br(),
                                                ]
                                            ),
                                        ]
                                    ),
                                    width=7,
                                ),
                            ],
                            justify="around",
                        )
                    ],
                ),
            ]
        ),
    ],
)


@app.callback(
    [Output("update_titles", "children"), Output("graph", "figure")],
    [
        Input("int", "n_intervals"),
        Input("data-select", "value"),
        Input("stop-button", "n_clicks"),
    ],
)
def save_cache(n, choice, n1):
    if n1 % 2 == 1:
        raise PreventUpdate

    if n is None:
        raise PreventUpdate

    if choice is None or choice == []:
        choice = ["Temperature", "Humidity", "CO2"]

    cache.clear()
    df = get_cache()
    df.dropna()
    temperature, co2, humidity = (
        df["Temperature"].iloc[-1],
        df["CO2"].iloc[-1],
        df["Humidity"].iloc[-1],
    )

    fig = dict(
        data=[
            dict(
                x=df["Time"],
                y=df[value],
                type="line",
                name=value,
            )
            for value in choice
        ],
        layout=dict(
            title="Sensor readings over time",
            showlegend=True,
            legend=dict(orientation="h", y=100),
            yaxis=dict(
                title="Sensor reading",
                titlefont=dict(size=14),
                tickfont=dict(size=14),
            ),
            xaxis=dict(
                title="Time",
                titlefont=dict(size=14),
                tickfont=dict(size=14),
            ),
        ),
    )

    titles = [
        html.H4(f"Temperature : {temperature}°C", id="temperature"),
        html.H4(f"Humidity : {humidity}%", id="humidity"),
        html.H4(f"CO2 level : {co2}%", id="co2"),
    ]

    return [titles, fig]


@app.callback(
    Output("download_plot", "data"),
    [
        Input("download-button", "n_clicks"),
    ],
)
def return_csv(n):
    ctx = dash.callback_context

    if not ctx.triggered:
        raise PreventUpdate
    else:
        button_id = ctx.triggered[0]["prop_id"].split(".")[0]

    if button_id == "download-button":
        data_sim = get_cache()
        return dict(content=data_sim.to_csv(index=False), filename="plot.csv")


if __name__ == "__main__":
    app.run_server(debug=True)
