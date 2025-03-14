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

load_dotenv()

# Connecting MongoDb database
client = MongoClient(os.getenv("mongodb_conn_str"))
db = client.finance

# Configure session to use mongodb (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "mongodb"
app.config["SESSION_MONGODB"] = client
app.config["SESSION_MONGODB_DB"] = "sessions"
app.config["SESSION_MONGODB_COLLECT"] = "sessions"
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")
Session(app)

@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""

    user_id = session["user_id"]
    
    stocks_owned_cursor = db.stocks_owned.find({"user_id": user_id})
    stocks_owned = list(stocks_owned_cursor)

    user = db.users.find_one({"_id": ObjectId(user_id)})
    cash = user["cash"] if user else 10000.0

    if not stocks_owned:
        return render_template("index.html", stocks_owned=[], Cash=cash, Total=cash)

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
            "total": round(cost * float(stocks["no_of_stocks"]), 2)
        }
        portfolio.append(transaction)

    return render_template("index.html", stocks_owned=portfolio, Cash=round(float(cash), 2), Total=round(float(cash + grand_total), 2))


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

        stocks = lookup(stock)

        if not stocks:
            return apology("enter a valid stock symbol", 400)

        if stock_no <= 0:
            return apology("enter a valid number", 400)

        user_id = session["user_id"]
        user = db.users.find_one({"_id" : ObjectId(user_id)})
        cash = float(user["cash"])

        cost = stock_no * float(stocks["price"])

        if cost > cash:
            return apology("you don't have sufficient funds", 400)
        
        # insert into transactions
        db.transactions.insert_one({
            "user_id" : ObjectId(user_id),
            "stock_name" : stocks["symbol"],
            "no_of_stocks" : stock_no,
            "price" : stocks["price"],
            "time" : datetime.datetime.now()
        })

        # update user's cash
        db.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"cash": cash - cost}}
        )

        # inserting ito stocks_owned
        db.stocks_owned.update_one(
            {"user_id": user_id, "stock_name": stocks["symbol"]},
            {"$inc": {"no_of_stocks": stock_no}},
            upsert=True
        )

        flash("Stock Bought successfully!", "success")

        return redirect("/")

    else:
        return render_template("buy.html")


@app.route("/history")
@login_required
def history():
    user_id = session["user_id"]

    stocks_transacted = list(db.transactions.find({"user_id" : ObjectId(user_id)}))

    transactions = [{
        "symbol": stock["stock_name"],
        "number of stocks": stock["no_of_stocks"],
        "price": stock["price"],
        "time": stock["time"]
    } for stock in stocks_transacted]

    return render_template("history.html", transactions=transactions)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 400)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 400)

        # Query database for username
        
        username = request.form.get("username")
        user = db.users.find_one({"username" : username})

        # Ensure username exists and password is correct
        if user is None or not check_password_hash(user["hash"], request.form.get("password")): 
            return apology("invalid username and/or password", 400)

        # Remember which user has logged in
        session["user_id"] = user["_id"]

        flash("Logged in successfully!", "success")

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():

    # Forget any user_id
    session.clear()

    # Redirect user to login form

    flash("logged out successfully!", "success")

    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == "POST":
        if not request.form.get("symbol"):
            return apology("provide a symbol", 400)
        symbol = request.form.get("symbol")
        stocks = lookup(symbol)
        fig = display_candlestick('slider', symbol).to_html(full_html=False, config={'displayModeBar': False})
        if not stocks:
            return apology("invalid symbol", 400)
        return render_template("quoted.html", stocks = stocks, fig = fig)
    else:
        return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":

        # ensuring username
        if not request.form.get("username"):
            return apology("must provide username", 400)

        # ensuring password
        if not request.form.get("password"):
            return apology("must provide password", 400)

        # ensuring if same username exists or not
        username = request.form.get("username")
        if db.users.find_one({"username" : username}):
            return apology("username already exists", 400)

        password = request.form.get("password")
        if not password:
            return apology("must provide password", 400)

        confirm = request.form.get("confirmation")
        if not confirm:
            return apology("enter the password again")

        if password != confirm:
            return apology("input same password in confirm password", 400)

        db.users.insert_one({
            "username" : username,
            "hash" : generate_password_hash(password),
            "cash" : 10000.00
        })

        user = db.users.find_one({"username" : username})
        session["user_id"] = user["_id"]

        flash("Registered successfully!", "success")

        return redirect("/")

    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    if request.method == "POST":
        stock = request.form.get("symbol")
        number = int(request.form.get("shares"))

        stock_val = db.stocks_owned.find_one({"user_id" : session["user_id"], "stock_name" : stock})

        if stock_val["no_of_stocks"] < number:
            return apology("you don't have sufficient stocks", 400)

        value = lookup(stock)

        db.transactions.insert_one({"user_id" : session["user_id"], "stock_name" : stock, "no_of_stocks" : -number, "price" : float(value["price"])})

        db.users.update_one(
            {"_id" : session["user_id"]},
            {"$inc": {"cash": number * float(value["price"])}}
        )

        if stock_val["no_of_stocks"] == number:
            db.stocks_owned.delete_one({"user_id": session["user_id"], "stock_name": stock})
        else:
            db.stocks_owned.update_one(
                {"user_id": session["user_id"], "stock_name": stock},
                {"$inc": {"no_of_stocks": -number}}
            )

        flash("Stocks sold successfully!", "success")

        return redirect("/")
    else:
        stock_val = db.stocks_owned.find({"user_id" : session["user_id"]})
        stock_names = [stock["stock_name"] for stock in stock_val]

        return render_template("sell.html", options=stock_names)


@app.route("/changepassword", methods=["GET", "POST"])
@login_required
def change_password():
    """Change the Password of user"""
    if request.method == "POST":
        password = request.form.get("password")
        new_password = request.form.get("new_password")
        confirmation = request.form.get("confirmation")

        if not password or not new_password or not confirmation:
            return apology("enter the password/passwords", 400)

        user = db.users.find_one({"_id" : session["user_id"]})
        pass_hash = user["hash"]

        if not pass_hash or not check_password_hash(pass_hash, password):  
            return apology("The password is incorrect", 400)

        if new_password != confirmation:
            return apology("The passwords are not the same", 400)

        db.users.update(
            {"_id" : user["_id"]},
            {"$set" : {"hash" : generate_password_hash(new_password)}}
        )

        flash("Password updated successfully!", "success")

        return redirect("/")

    else:
        return render_template("change.html")