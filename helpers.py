import os
import requests
import polars as pl
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
        response = requests.get(f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={symbol}&outputsize=compact&apikey={os.getenv('lookup_api_key')}")
        response.raise_for_status()

        data = response.json()
        raw_df = data.get('Time Series (Daily)', {})

        # Convert JSON to Polars DataFrame
        df = pl.DataFrame(raw_df).transpose(include_header=True)  # Transpose to get the correct format
        
        # Rename columns and parse index as datetime
        df = df.rename({"column_0": "date", "column_1": "Open", "column_2": "High", 
                        "column_3": "Low", "column_4": "Close", "column_5": "Volume"})
        
        # Convert date column to datetime
        df = df.with_columns(pl.col("date").str.to_datetime())

    except (KeyError, IndexError, requests.RequestException, ValueError):
        return None

    # Convert polars DataFrame to dictionary for Plotly
    fig = go.Figure(go.Candlestick(
        x=df["date"].to_list(),
        open=df["Open"].to_list(),
        high=df["High"].to_list(),
        low=df["Low"].to_list(),
        close=df["Close"].to_list()
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
