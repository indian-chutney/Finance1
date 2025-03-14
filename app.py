from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd, display_candlestick

# Configure application
app = Flask(__name__)

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_TYPE"] = "securecookie"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")


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
    table = db.execute("SELECT stock_name, no_of_stocks FROM stocks_owned WHERE id = ?", user_id)
    print(table)

    cash = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])

    if not table:
        return render_template("index.html", stocks_owned=[], Cash=cash[0]["cash"], Total=cash[0]["cash"])

    n = len(table)
    stocks_owned = []
    grand_total = 0
    for i in range(n):
        stock = lookup(table[i]["stock_name"])
        cost = float(stock["price"])
        grand_total = grand_total + cost * float(table[i]["no_of_stocks"])
        transaction = {
            "stock": table[i]["stock_name"],
            "number of stocks": int(table[i]["no_of_stocks"]),
            "price": cost,
            "total": round(cost * float(table[i]["no_of_stocks"]), 2)
        }
        stocks_owned.append(transaction)

    return render_template("index.html", stocks_owned=stocks_owned, Cash=round(float(cash[0]["cash"]), 2), Total=round(float(cash[0]["cash"] + grand_total), 2))


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

        value = db.execute("SELECT cash FROM users WHERE id = ?", user_id)

        cash = float(value[0]["cash"])

        cost = stock_no * float(stocks["price"])

        if cost > cash:
            return apology("you don't have sufficient funds", 400)

        db.execute("INSERT INTO transactions(id, stock_name, no_of_stocks, price) VALUES(?, ?, ?, ?)",
                   session["user_id"], stocks["symbol"], stock_no, float(stocks["price"]))

        db.execute("UPDATE users SET cash = ? WHERE id = ?", cash - cost, session["user_id"])

        db.execute("INSERT INTO stocks_owned (id, stock_name, no_of_stocks) VALUES (?, ?, ?) ON CONFLICT(id, stock_name) DO UPDATE SET no_of_stocks = no_of_stocks + excluded.no_of_stocks",
                   session["user_id"], stocks["symbol"], stock_no)

        flash("Stock Bought successfully!", "success")

        return redirect("/")

    else:
        return render_template("buy.html")


@app.route("/history")
@login_required
def history():

    table = db.execute(
        "SELECT stock_name, no_of_stocks, price, time FROM transactions WHERE id = ?", session["user_id"])
    n = len(table)

    transactions = []

    for i in range(n - 1, -1, -1):
        transaction = {
            "symbol": table[i]["stock_name"],
            "number of stocks": table[i]["no_of_stocks"],
            "price": table[i]["price"],
            "time": table[i]["time"]
        }
        transactions.append(transaction)

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
        rows = db.execute(
            "SELECT * FROM users WHERE username = ?", request.form.get("username")
        )

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(
            rows[0]["hash"], request.form.get("password")
        ):
            return apology("invalid username and/or password", 400)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

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
        if db.execute("SELECT username FROM users WHERE username = ?", username):
            return apology("username already exists", 400)

        # checking for strong password
        password = request.form.get("password")
        if not password:
            return apology("must provide password", 400)

        confirm = request.form.get("confirmation")
        if not confirm:
            return apology("enter the password again")

        if password != confirm:
            return apology("input same password in confirm password", 400)

        db.execute("INSERT INTO users(username, hash) VALUES(?, ?)",
                   username, generate_password_hash(password))

        id = db.execute(
            "SELECT id FROM users WHERE username = ?", username
        )

        print(id[0]["id"])

        session["user_id"] = id[0]["id"]

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

        row = db.execute(
            "SELECT no_of_stocks FROM stocks_owned WHERE stock_name = ? AND id = ?", stock, session["user_id"])

        if row[0]["no_of_stocks"] < number:
            return apology("you don't have sufficient stocks", 400)

        value = lookup(stock)

        db.execute("INSERT INTO transactions(id, stock_name, no_of_stocks, price) VALUES(?, ?, ?, ?)",
                   session["user_id"], stock, 0 - number, float(value["price"]))

        if row[0]["no_of_stocks"] == number:
            db.execute("DELETE FROM stocks_owned WHERE id = ? AND stock_name = ?",
                       session["user_id"], stock)
        else:
            db.execute("UPDATE stocks_owned SET no_of_stocks = ? WHERE id = ? AND stock_name = ?",
                       row[0]["no_of_stocks"] - number, session["user_id"], stock)

        db.execute("UPDATE users SET cash = cash + ? WHERE id = ?",
                   number * float(value["price"]), session["user_id"])

        flash("Stocks sold successfully!", "success")

        return redirect("/")
    else:
        options = db.execute("SELECT stock_name FROM stocks_owned WHERE id = ?", session["user_id"])
        stock_names = [option['stock_name'] for option in options]

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

        pass_hash = db.execute("SELECT hash FROM users WHERE id = ?",session["user_id"])

        if not check_password_hash(pass_hash[0]["hash"], password):
            return apology("The password is incorrect", 400)

        if new_password != confirmation:
            return apology("The passwords are not same", 400)

        db.execute("UPDATE users SET hash = ? WHERE id = ?", generate_password_hash(new_password), session["user_id"])

        flash("Password updated successfully!", "success")

        return redirect("/")

    else:
        return render_template("change.html")