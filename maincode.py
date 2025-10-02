import ccxt
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
import dash
from dash import dcc, html
from dash.dependencies import Input, Output

# -------------------------------
# 거래소 연결
# -------------------------------
exchange = ccxt.binance()

# -------------------------------
# 데이터 가져오기
# -------------------------------
def fetch_ohlcv(symbol="BTC/USDT", timeframe="1m", limit=1000):
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    return df

# -------------------------------
# 패턴 탐색 (하루에 1개만)
# -------------------------------
def find_similar_patterns(df, window=150, forward=60, top_n=10):
    current = df["close"].iloc[-window:].values
    similarities = []

    for i in range(len(df) - window - forward):
        past = df["close"].iloc[i:i+window].values
        if len(past) < window:
            continue
        corr = np.corrcoef(current, past)[0, 1]
        timestamp = df["timestamp"].iloc[i+window]
        similarities.append((corr, i, timestamp))

    similarities.sort(key=lambda x: x[0], reverse=True)

    picked = {}
    results = []
    for corr, idx, ts in similarities:
        day = ts.strftime("%Y-%m-%d")
        if day not in picked:
            picked[day] = True
            results.append((corr, idx, ts))
        if len(results) >= top_n:
            break

    return results

# -------------------------------
# 차트 생성
# -------------------------------
def create_figure(symbol="BTC/USDT", timeframe="1m", limit=1000, top_n=5):
    df = fetch_ohlcv(symbol, timeframe, limit)

    window = 150
    forward = 60

    current = df.iloc[-window-forward:]
    current_trace = go.Scatter(
        x=np.arange(-window, forward),
        y=current["close"].values,
        mode="lines",
        name="CURRENT",
        line=dict(color="white", width=2)
    )

    patterns = find_similar_patterns(df, window=window, forward=forward, top_n=top_n)

    pattern_traces = []
    colors = ["red", "orange", "green", "cyan", "magenta", "yellow"]
    for i, (corr, idx, ts) in enumerate(patterns):
        past = df.iloc[idx:idx+window+forward]
        trace = go.Scatter(
            x=np.arange(-window, forward),
            y=past["close"].values,
            mode="lines",
            name=f"PATTERN {i+1} ({ts.strftime('%Y-%m-%d')})",
            line=dict(color=colors[i % len(colors)], width=1, dash="dot")
        )
        pattern_traces.append(trace)

    fig = go.Figure([current_trace] + pattern_traces)
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="black",
        plot_bgcolor="black",
        font=dict(family="Oswald", color="white", size=14),
        title=f"{symbol} {timeframe} PATTERN ANALYSIS",
        xaxis=dict(title="BARS (CURRENT = 0)"),
        yaxis=dict(title="PRICE")
    )

    return fig

# -------------------------------
# Dash UI
# -------------------------------
app = dash.Dash(__name__)

app.layout = html.Div(
    style={"backgroundColor": "black", "padding": "20px", "fontFamily": "Oswald"},
    children=[
        html.H1("REAL-TIME PATTERN MATCHING", 
                style={"textAlign": "center", "color": "white"}),

        dcc.Graph(id="chart", style={"height": "80vh"}),

        # ---------------- Settings Section (밑으로 내림)
        html.Div([
            html.Div([
                html.Label("COIN", style={"color": "white"}),
                dcc.Dropdown(
                    id="coin-dropdown",
                    options=[
                        {"label": "BTC/USDT", "value": "BTC/USDT"},
                        {"label": "ETH/USDT", "value": "ETH/USDT"},
                        {"label": "XRP/USDT", "value": "XRP/USDT"}
                    ],
                    value="BTC/USDT",
                    clearable=False,
                    style={"width": "200px", "color": "black"}
                ),
            ], style={"marginBottom": "20px"}),

            html.Div([
                html.Label("TIMEFRAME", style={"color": "white"}),
                dcc.Dropdown(
                    id="timeframe-dropdown",
                    options=[
                        {"label": "1M", "value": "1m"},
                        {"label": "5M", "value": "5m"},
                        {"label": "15M", "value": "15m"},
                        {"label": "30M", "value": "30m"},
                        {"label": "1H", "value": "1h"},
                    ],
                    value="1m",
                    clearable=False,
                    style={"width": "200px", "color": "black"}
                ),
            ], style={"marginBottom": "20px"}),

            html.Div([
                html.Label("MAX BARS", style={"color": "white"}),
                dcc.Slider(
                    id="max-bars-slider",
                    min=1000,
                    max=1000000,
                    step=1000,
                    value=100000,
                    marks={1000: "1K", 100000: "100K", 500000: "500K", 1000000: "1M"},
                    tooltip={"placement": "bottom"}
                ),
            ], style={"marginBottom": "40px"}),

            html.Div([
                html.Label("TOP N PATTERNS", style={"color": "white"}),
                dcc.Slider(
                    id="top-n-slider",
                    min=1,
                    max=10,
                    step=1,
                    value=5,
                    marks={i: str(i) for i in range(1, 11)},
                    tooltip={"placement": "bottom"}
                ),
            ], style={"marginBottom": "40px"}),
        ])
    ]
)

# -------------------------------
# 콜백
# -------------------------------
@app.callback(
    Output("chart", "figure"),
    [Input("coin-dropdown", "value"),
     Input("timeframe-dropdown", "value"),
     Input("max-bars-slider", "value"),
     Input("top-n-slider", "value")]
)
def update_chart(coin, timeframe, max_bars, top_n):
    return create_figure(coin, timeframe, max_bars, top_n)

# -------------------------------
if __name__ == "__main__":
    app.run(port=8060)
