import os
import datetime

from flask import Flask, flash, redirect, render_template, request, session
from dotenv import load_dotenv
from pymongo import MongoClient
from bson.objectid import ObjectId
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd, display_candlestick

# Configure application
app = Flask(__name__)

# Custom filter
app.jinja_env.filters["usd"] = usd

# loading environment variables
load_dotenv()

# Connecting MongoDb database
client = MongoClient(os.getenv("mongodb_conn_str"))
db = client.finance

# Configuring session to use mongodb (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "mongodb"
app.config["SESSION_MONGODB"] = client
app.config["SESSION_MONGODB_DB"] = "sessions"
app.config["SESSION_MONGODB_COLLECT"] = "sessions"
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")
Session(app)


# Ensuring responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


# homepage route
@app.route("/")
@login_required
def index():
    # displaying portfolio of stocks owned

    user_id = session["user_id"]

    # fetching stocks owned by user from db
    stocks_owned_cursor = db.stocks_owned.find({"user_id": ObjectId(user_id)})
    stocks_owned = list(stocks_owned_cursor)

    user = db.users.find_one({"_id": ObjectId(user_id)})
    cash = user["cash"] if user else 10000.0

    if not stocks_owned:
        return render_template("index.html", stocks_owned=[], Cash=cash, Total=cash)

    # making portfolio list for rendering
    portfolio = []
    grand_total = 0
    for stocks in stocks_owned:
        stock = lookup(stocks["stock_name"])
        cost = float(stock["price"])
        grand_total = grand_total + cost * float(stocks["no_of_stocks"])
        transaction = {
            "stock": stocks["stock_name"],
            "number of stocks": int(stocks["no_of_stocks"]),
            "price": cost,
            "total": round(cost * float(stocks["no_of_stocks"]), 2),
        }
        portfolio.append(transaction)

    # rendering portfolio on homepage
    return render_template(
        "index.html",
        stocks_owned=portfolio,
        Cash=round(float(cash), 2),
        Total=round(float(cash + grand_total), 2),
    )


# route for buying stocks
@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    if request.method == "POST":
        if not request.form.get("symbol"):
            return apology("provide a symbol", 400)

        stock = request.form.get("symbol")
        stock_no = request.form.get("shares")

        if not (stock_no.isdigit() and int(stock_no) > 0):
            return apology("enter a countable number")

        stock_no = int(stock_no)

        # fetch stock data from api
        stocks = lookup(stock)

        if not stocks:
            return apology("enter a valid stock symbol", 400)

        if stock_no <= 0:
            return apology("enter a valid number", 400)

        # fetch user's data from db
        user_id = session["user_id"]
        user = db.users.find_one({"_id": ObjectId(user_id)})
        cash = float(user["cash"])

        cost = stock_no * float(stocks["price"])

        if cost > cash:
            return apology("you don't have sufficient funds", 400)

        # insert into transactions
        db.transactions.insert_one(
            {
                "user_id": ObjectId(user_id),
                "stock_name": stocks["symbol"],
                "no_of_stocks": stock_no,
                "price": stocks["price"],
                "time": datetime.datetime.now(),
            }
        )

        # update user's cash
        db.users.update_one({"_id": ObjectId(user_id)}, {"$set": {"cash": cash - cost}})

        # inserting into stocks_owned
        db.stocks_owned.update_one(
            {"user_id": ObjectId(user_id), "stock_name": stocks["symbol"]},
            {"$inc": {"no_of_stocks": stock_no}},
            upsert=True,
        )

        flash("Stock Bought successfully!", "success")

        return redirect("/")

    else:
        return render_template("buy.html")


# route to display history of all transactions by user
@app.route("/history")
@login_required
def history():
    user_id = session["user_id"]

    # fetching user's stocks from db
    stocks_transacted = list(db.transactions.find({"user_id": ObjectId(user_id)}))

    # making transactions list for rendering on page
    transactions = [
        {
            "symbol": stock["stock_name"],
            "no_of_stocks": stock["no_of_stocks"],
            "price": stock["price"],
            "time": stock["time"],
        }
        for stock in stocks_transacted
    ]

    return render_template("history.html", transactions=transactions[::-1])


# route handler for getting stock data from api
@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    if request.method == "POST":
        if not request.form.get("symbol"):
            return apology("provide a symbol", 400)

        symbol = request.form.get("symbol")

        # fetching current price of stock
        try:
            stocks = lookup(symbol)

            # fetching data of last 100 days from api and generating candlestick graph
            fig = display_candlestick("slider", symbol).to_html(
                full_html=False, config={"displayModeBar": False}
            )

            if not stocks:
                return apology("invalid symbol", 400)

            # rendering graph and table
            return render_template("quoted.html", stocks=stocks, fig=fig)
        except:
            return apology("Invalid Stock Symbol", 400)

    else:
        return render_template("quote.html")


# route for signing out user
@app.route("/logout")
def logout():
    # Forget any user_id
    session.clear()

    # Redirect user to login form
    flash("logged out successfully!", "success")

    return redirect("/")


# route handler for selling stocks owned by user
@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    if request.method == "POST":
        stock = request.form.get("symbol")
        number = int(request.form.get("shares"))

        if number <= 0:
            return apology("Enter Valid Number", 400)

        # fetching user's stocks
        stock_val = db.stocks_owned.find_one(
            {"user_id": ObjectId(session["user_id"]), "stock_name": stock}
        )

        if stock_val["no_of_stocks"] < number:
            return apology("you don't have sufficient stocks", 400)

        # fetching current price of given stock
        try:
            value = lookup(stock)

            # inserting stock sold into transactions collection
            db.transactions.insert_one(
                {
                    "user_id": ObjectId(session["user_id"]),
                    "stock_name": stock,
                    "no_of_stocks": -number,
                    "price": float(value["price"]),
                    "time": datetime.datetime.now(),
                }
            )

            # updating user's balance
            db.users.update_one(
                {"_id": ObjectId(session["user_id"])},
                {"$inc": {"cash": number * float(value["price"])}},
            )

            # updating value of stocks owned by user
            if stock_val["no_of_stocks"] == number:
                db.stocks_owned.delete_one(
                    {"user_id": ObjectId(session["user_id"]), "stock_name": stock}
                )
            else:
                db.stocks_owned.update_one(
                    {"user_id": ObjectId(session["user_id"]), "stock_name": stock},
                    {"$set": {"no_of_stocks": stock_val["no_of_stocks"] - number}},
                )

            flash("Stocks sold successfully!", "success")

            return redirect("/")
        except:
            return apology("Invalid Stock Symbol", 400)
    else:
        stock_val = db.stocks_owned.find({"user_id": ObjectId(session["user_id"])})
        stock_names = [stock["stock_name"] for stock in stock_val]

        # rendering stocks owned in options bar
        return render_template("sell.html", options=stock_names)


# route handler for changing password
@app.route("/changepassword", methods=["GET", "POST"])
@login_required
def change_password():
    if request.method == "POST":
        password = request.form.get("password")
        new_password = request.form.get("new_password")
        confirmation = request.form.get("confirmation")

        if not password or not new_password or not confirmation:
            return apology("enter the password/passwords", 400)

        # fetching user's data
        user = db.users.find_one({"_id": ObjectId(session["user_id"])})
        pass_hash = user["hash"]

        # check if hash of user's password is same as given
        if not pass_hash or not check_password_hash(pass_hash, password):
            return apology("The password is incorrect", 400)

        if new_password != confirmation:
            return apology("The passwords are not the same", 400)

        # updating user's password
        db.users.update_one(
            {"_id": user["_id"]},
            {"$set": {"hash": generate_password_hash(new_password)}},
        )

        flash("Password updated successfully!", "success")

        return redirect("/")

    else:
        return render_template("change.html")


# route handler for login page
@app.route("/login", methods=["GET", "POST"])
def login():
    # Forget any user_id
    session.clear()

    if request.method == "POST":
        if not request.form.get("username"):
            return apology("must provide username", 400)

        elif not request.form.get("password"):
            return apology("must provide password", 400)

        # fetching 'username' data from db
        username = request.form.get("username")
        user = db.users.find_one({"username": username})

        # Ensuring username exists and password is correct
        if user is None or not check_password_hash(
            user["hash"], request.form.get("password")
        ):
            return apology("invalid username and/or password", 400)

        # Remember which user has logged in
        session["user_id"] = str(user["_id"])

        flash("Logged in successfully!", "success")

        # Redirect user to home page
        return redirect("/")

    else:
        return render_template("login.html")


# route handler for registering a user
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        if not request.form.get("username"):
            return apology("must provide username", 400)

        if not request.form.get("password"):
            return apology("must provide password", 400)

        # ensuring if same username exists or not
        username = request.form.get("username")
        if db.users.find_one({"username": username}):
            return apology("username already exists", 400)

        password = request.form.get("password")
        if not password:
            return apology("must provide password", 400)

        confirm = request.form.get("confirmation")
        if not confirm:
            return apology("enter the password again")

        if password != confirm:
            return apology("input same password in confirm password", 400)

        # inserting new user data into users collection
        db.users.insert_one(
            {
                "username": username,
                "hash": generate_password_hash(password),
                "cash": 10000.00,
            }
        )

        user = db.users.find_one({"username": username})

        # configuring session
        session["user_id"] = str(user["_id"])

        flash("Registered successfully!", "success")

        return redirect("/")

    else:
        return render_template("register.html")
