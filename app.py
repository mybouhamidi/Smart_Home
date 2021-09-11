import pyrebase
import dash
from flask_caching import Cache
import dash_bootstrap_components as dbc
import dash_daq as daq
import dash_html_components as html
import dash_core_components as dcc
from dash_extensions.enrich import Input, Output
import password

config = {
    "apiKey": password.API_KEY,
    "authDomain": password.AUTH_DOMAIN,
    "databaseURL": password.DATABASE_URL,
    "storageBucket": password.STORAGE_BUCKET,
}

app = dash.Dash(
    __name__,
    title="Smart Home",
    update_title=None,
    suppress_callback_exceptions=True,
    meta_tags=[
        {"name": "viewport", "content": "width=device-width, initial-scale=1"},
    ],
)

cache = Cache(
    app.server, config={"CACHE_TYPE": "filesystem", "CACHE_DIR": "cache-directory"}
)
server = app.server

cache.set("data", {"Time": [], "Hall": [], "Touch": [], "Touch-1": []})

TIMEOUT = 10
# Call to Firebase
@cache.memoize(timeout=TIMEOUT)
def call_firebase():
    firebase = pyrebase.initialize_app(config)
    db = firebase.database()
    temp = db.child("Living Room").get()
    df = cache.get("data")
    df["Time"].append(temp.val()["Hall"]["time"])
    df["Hall"].append(temp.val()["Hall"]["value"])
    df["Touch"].append(temp.val()["Touch"]["value"])
    df["Touch-1"].append(temp.val()["Touch-1"]["value"])
    cache.set("data", df)


app.layout = html.Div(
    html.Div(
        [
            html.Div(
                id="display",
                children=[
                    html.Div(
                        [
                            dbc.Row(
                                [
                                    dbc.Row(
                                        [
                                            html.Div(
                                                [
                                                    daq.Gauge(
                                                        id="touch_daq",
                                                        max=2000,
                                                    ),
                                                ],
                                                style={
                                                    "height": "400px",
                                                    "display": "inline-block",
                                                },
                                            ),
                                            html.Div(
                                                [
                                                    daq.Gauge(
                                                        id="hall_daq",
                                                        max=2000,
                                                    ),
                                                ],
                                                style={
                                                    "height": "400px",
                                                    "display": "inline-block",
                                                },
                                            ),
                                            html.Div(
                                                [
                                                    daq.Gauge(
                                                        id="touch_1_daq",
                                                        max=2000,
                                                    ),
                                                ],
                                                style={
                                                    "height": "400px",
                                                    "display": "inline-block",
                                                },
                                            ),
                                        ],
                                        style={"height": "400px"},
                                    )
                                ]
                            ),
                            dbc.Row([dcc.Graph(id="graph")]),
                        ]
                    )
                ],
            ),
            dcc.Interval(id="int", interval=10000, n_intervals=0),
        ]
    )
)


@app.callback(
    [
        Output("touch_daq", "value"),
        Output("touch_1_daq", "value"),
        Output("hall_daq", "value"),
        Output("graph", "figure"),
    ],
    [Input("int", "n_intervals")],
)
def print(n):
    call_firebase()
    df = cache.get("data")
    touch = df["Touch"][-1]
    hall = df["Hall"][-1]
    touch_1 = df["Touch-1"][-1]

    fig = dict(
        data=[
            dict(
                x=df["Time"],
                y=df["Hall"],
                type="scatter",
                name="Hall",
            ),
            dict(
                x=df["Time"],
                y=df["Touch"],
                type="scatter",
                name="Touch",
            ),
            dict(
                x=df["Time"],
                y=df["Touch-1"],
                type="scatter",
                name="Touch-1",
            ),
        ],
        layout=dict(
            title="Time series",
            yaxis=dict(
                title="Sensor reading",
                titlefont=dict(size=18),
                tickfont=dict(size=18),
            ),
            xaxis=dict(
                title="Time",
                titlefont=dict(size=18),
                tickfont=dict(size=18),
            ),
        ),
    )

    return [touch, touch_1, hall, fig]


if __name__ == "__main__":
    app.run_server(debug=True)
