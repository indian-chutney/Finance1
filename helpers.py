import os
import requests
import pandas as pd
import plotly.graph_objects as go

from dotenv import load_dotenv
from flask import redirect, render_template, session
from functools import wraps


def apology(message, code=400):

    def escape(s):
    # reference -> https://github.com/jacebrowning/memegen#special-characters

        for old, new in [
            ("-", "--"),
            (" ", "-"),
            ("_", "__"),
            ("?", "~q"),
            ("%", "~p"),
            ("#", "~h"),
            ("/", "~s"),
            ('"', "''"),
        ]:
            s = s.replace(old, new)
        return s

    return render_template("apology.html", top=code, bottom=escape(message)), code


def login_required(f):

    # referece -> https://flask.palletsprojects.com/en/latest/patterns/viewdecorators/

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)

    return decorated_function


def lookup(symbol):

    load_dotenv()

    symbol = symbol.upper()

    url = (
        f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}&apikey={os.getenv("lookup_api_key")}"
    )

    # Query API
    try:
        response = requests.get(url)
        response.raise_for_status()

        data = response.json()

        price = round(float(data["Global Quote"]["05. price"]), 2)
        stock_val = {"price": price, "symbol": symbol}

        return stock_val

    except (KeyError, IndexError, requests.RequestException, ValueError):
        return None


# reference -> https://plotly.com/python/candlestick-charts/
def display_candlestick(value, symbol):
    try:
        response = requests.get(f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={symbol}&outputsize=compact&apikey={os.getenv("lookup_api_key")}")
        response.raise_for_status()

        data = response.json()
        df = pd.DataFrame(data['Time Series (Daily)']).T
        df.index = pd.to_datetime(df.index)
        df.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
    except (KeyError, IndexError, requests.RequestException, ValueError):
        return None

    fig = go.Figure(go.Candlestick(
        x=df.index,
        open=df['Open'],
        high=df['High'],
        low=df['Low'],
        close=df['Close']
    ))

    fig.update_layout(
        xaxis_rangeslider_visible='slider' in value,
        title=dict(
            text=f"{symbol} Stock Chart", 
            font=dict(color="#00acc2", size=20, weight="bold")  # Bold, #00acc2, size 20
        ),
        xaxis=dict(
            title=dict(text="Date", font=dict(color="#00acc2", size=16)),  # Bold X label
            tickfont=dict(color="#00acc2", size=14)  # X-axis tick labels
        ),
        yaxis=dict(
            title=dict(text="Price", font=dict(color="#00acc2", size=16)),  # Bold Y label
            tickfont=dict(color="#00acc2", size=14)  # Y-axis tick labels
        ),
        font=dict(color="#00acc2", size=14),  # Default text settings (legend, tooltips)
        paper_bgcolor="black",  # Outer background
    )

    return fig

def usd(value):
    return f"${value:,.2f}"
