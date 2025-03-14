import sqlite3
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

# Connect to SQLite database
conn = sqlite3.connect("finance.db", check_same_thread=False)
cursor = conn.cursor()


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
    cursor.execute("SELECT stock_name, no_of_stocks FROM stocks_owned WHERE id = ?", (user_id,))
    table = cursor.fetchall()

    cursor.execute("SELECT cash FROM users WHERE id = ?", (session["user_id"],))
    cash = cursor.fetchone()

    if not table:
        return render_template("index.html", stocks_owned=[], Cash=cash[0], Total=cash[0])

    stocks_owned = []
    grand_total = 0
    for row in table:
        stock = lookup(row[0])
        cost = float(stock["price"])
        grand_total = grand_total + cost * float(row[1])
        transaction = {
            "stock": row[0],
            "number of stocks": int(row[1]),
            "price": cost,
            "total": round(cost * float(row[1]), 2)
        }
        stocks_owned.append(transaction)

    return render_template("index.html", stocks_owned=stocks_owned, Cash=round(float(cash[0]), 2), Total=round(float(cash[0] + grand_total), 2))


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

        cursor.execute("SELECT cash FROM users WHERE id = ?", (user_id,))
        cash = float(cursor.fetchone()[0])

        cost = stock_no * float(stocks["price"])

        if cost > cash:
            return apology("you don't have sufficient funds", 400)

        cursor.execute("INSERT INTO transactions(id, stock_name, no_of_stocks, price) VALUES(?, ?, ?, ?)", (user_id, stocks["symbol"], stock_no, float(stocks["price"])))
        cursor.execute("UPDATE users SET cash = ? WHERE id = ?", (cash - cost, user_id))
        cursor.execute("INSERT INTO stocks_owned (id, stock_name, no_of_stocks) VALUES (?, ?, ?) ON CONFLICT(id, stock_name) DO UPDATE SET no_of_stocks = no_of_stocks + excluded.no_of_stocks", (user_id, stocks["symbol"], stock_no))
        conn.commit()

        flash("Stock Bought successfully!", "success")

        return redirect("/")

    else:
        return render_template("buy.html")


@app.route("/history")
@login_required
def history():

    cursor.execute("SELECT stock_name, no_of_stocks, price, time FROM transactions WHERE id = ?", (session["user_id"],))
    table = cursor.fetchall()

    transactions = [{
        "symbol": row[0],
        "number of stocks": row[1],
        "price": row[2],
        "time": row[3]
    } for row in table]

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
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()

        # Ensure username exists and password is correct
        if row is None or not check_password_hash(row[2], request.form.get("password")): 
            return apology("invalid username and/or password", 400)

        # Remember which user has logged in
        session["user_id"] = row[0]

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
        cursor.execute("SELECT username FROM users WHERE username = ?", (username,))
        if cursor.fetchone():
            return apology("username already exists", 400)

        password = request.form.get("password")
        if not password:
            return apology("must provide password", 400)

        confirm = request.form.get("confirmation")
        if not confirm:
            return apology("enter the password again")

        if password != confirm:
            return apology("input same password in confirm password", 400)

        cursor.execute("INSERT INTO users(username, hash) VALUES(?, ?)", (username, generate_password_hash(password)))
        conn.commit()
        cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
        session["user_id"] = cursor.fetchone()[0]

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

        cursor.execute("SELECT no_of_stocks FROM stocks_owned WHERE stock_name = ? AND id = ?", (stock, session["user_id"]))
        row = cursor.fetchone()

        if row[0] < number:
            return apology("you don't have sufficient stocks", 400)

        value = lookup(stock)

        cursor.execute("INSERT INTO transactions(id, stock_name, no_of_stocks, price) VALUES(?, ?, ?, ?)", (session["user_id"], stock, -number, float(value["price"])))
        cursor.execute("UPDATE users SET cash = cash + ? WHERE id = ?", (number * float(value["price"]), session["user_id"]))
        conn.commit()

        flash("Stocks sold successfully!", "success")

        return redirect("/")
    else:
        cursor.execute("SELECT stock_name FROM stocks_owned WHERE id = ?", (session["user_id"],))
        stock_names = [row[0] for row in cursor.fetchall()]

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

        cursor.execute("SELECT hash FROM users WHERE id = ?", (session["user_id"],))
        pass_hash = cursor.fetchone()

        if not pass_hash or not check_password_hash(pass_hash[0], password):  
            return apology("The password is incorrect", 400)

        if new_password != confirmation:
            return apology("The passwords are not the same", 400)

        cursor.execute("UPDATE users SET hash = ? WHERE id = ?", 
                       (generate_password_hash(new_password), session["user_id"]))
        conn.commit()

        flash("Password updated successfully!", "success")

        return redirect("/")

    else:
        return render_template("change.html")
