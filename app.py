import dash
import dash_auth
from flask_caching import Cache
import dash_bootstrap_components as dbc
import dash_daq as daq
import dash_html_components as html
import dash_core_components as dcc
from dash_extensions.enrich import Input, Output, PreventUpdate
from dash_extensions import Download
import pandas as pd

import json
import urllib.request
import sys
import os


def find_data_file(filename):
    if getattr(sys, "frozen", False):
        datadir = os.path.dirname(sys.executable)
    else:
        datadir = os.path.dirname(__file__)

    return os.path.join(datadir, filename)


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

auth = dash_auth.BasicAuth(app, {"admin": "admin"})

cache = Cache(
    app.server, config={"CACHE_TYPE": "filesystem", "CACHE_DIR": "cache-directory"}
)
server = app.server

cache.set("data", {})

TIMEOUT = 10
# Call to Firebase
@cache.memoize(timeout=TIMEOUT)
def call_thingspeak():
    contents = urllib.request.urlopen(
        "https://api.thingspeak.com/channels/1535860/feeds?api_key=DIH175GW6M7JGTLT&results=8000"
    ).read()

    text = contents.decode("utf-8")
    data = json.loads(text)
    df = {"Time": [], "Temperature": [], "Humidity": [], "CO2": []}
    for i in range(len(data["feeds"])):
        df["Time"].append(pd.Timestamp(data["feeds"][i]["created_at"]))
        df["Temperature"].append(data["feeds"][i]["field1"])
        df["Humidity"].append(data["feeds"][i]["field2"])
        df["CO2"].append((float(data["feeds"][i]["field3"]) / 4095) * 3.3)

    return pd.DataFrame(df, columns=["Time", "Temperature", "Humidity", "CO2"])


def get_cache():
    return call_thingspeak()


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
                                                        interval=2000,
                                                        n_intervals=0,
                                                    ),
                                                    html.Br(),
                                                ]
                                            ),
                                            dbc.Row(
                                                [
                                                    html.Div(id="slider"),
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
    [
        Output("update_titles", "children"),
        Output("graph", "figure"),
        # Output("slider","children"),
        # Output("cross-filter", "min"),
        # Output("cross-filter", "max"),
        # Output("cross-filter", "value"),
        # Output("cross-filter", "marks"),
    ],
    [Input("int", "n_intervals"), Input("data-select", "value")],
)
def save_cache(n, choice):
    if choice is None or choice == []:
        choice = ["Temperature", "Humidity", "CO2"]

    cache.clear()
    df = get_cache()
    cache.set("data", df)
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

    temperature, co2, humidity = (
        df["Temperature"].iloc[-1],
        df["CO2"].iloc[-1],
        df["Humidity"].iloc[-1],
    )
    titles = [
        html.H4(f"Temperature : {temperature}°C", id="temperature"),
        html.H4(f"Humidity : {humidity}%", id="humidity"),
        html.H4(f"CO2 level : {co2}%", id="co2"),
    ]

    # slider = dcc.Slider(id="cross-filer", marks={str(day): str(day) for day in df["Time"]}, min=df["Time"].min().day, value=df["Time"].min().day, max=df["Time"].max().day)

    return [
        titles,
        fig,
        # slider
    ]


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