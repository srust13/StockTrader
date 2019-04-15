import os
import sqlite3
from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)


# Configure CS50 Library to use SQLite database and create purchases table
db = SQL("sqlite:///finance.db")
#conn = sqlite3.connect('finance.db')
#db = conn.cursor()

#dropTableStatement = "DROP TABLE purchases"
#db.execute(dropTableStatement)

#db.execute('CREATE TABLE IF NOT EXISTS purchases (id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, user_id INTEGER NOT NULL, symbol TEXT NOT NULL, shares INTEGER NOT NULL, price NUMERIC NOT NULL, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)')
#db.execute('CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, username TEXT NOT NULL, hash TEXT NOT NULL, cash NUMERIC NOT NULL DEFAULT 10000.00 )')
#conn.commit()
#db.close()
#conn.close()


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""

    # look up the current user
    rows = db.execute("SELECT cash FROM users WHERE id = :user_id", user_id=session["user_id"])
    stocks = db.execute("SELECT symbol, SUM(shares) AS total_shares, price FROM purchases WHERE user_id = :user_id GROUP BY symbol", user_id=session["user_id"])
    
    currentBalance = rows[0]["cash"]     

    return render_template("index.html",  stocks=stocks, currentBalance=currentBalance)

@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""

    if request.method == "POST":    
        symbol=request.form.get("symbol")
        
        # Check if symbol exists
        quote=lookup(symbol)
        if quote==None:
            return apology("Please enter a valid ticker symbol")
        
        # Make sure shares is entered as a positive integer
        shares = request.form.get("shares")
        if not shares or not shares.isdigit() or float(shares)%1!=0 or int(shares)<1:
            return apology("The number of shares must be a positive integer :)")
        else:
            shares = int(request.form.get("shares"))

        # Query database for username
        rows = db.execute("SELECT cash FROM users WHERE id = :user_id", user_id=session["user_id"])

        # Check if enough funds are available for purchase
        sharePrice = quote["price"]
        currentBalance = rows[0]["cash"]
        cashNeeded = sharePrice*shares
        if cashNeeded > currentBalance:
            return apology("There are not enough funds in your account")

        # Update remaining balance and buy stocks
        db.execute("UPDATE users SET cash = cash - :price WHERE id = :user_id", price=cashNeeded, user_id=session["user_id"])
        db.execute("INSERT INTO purchases (user_id, symbol, shares, price) VALUES(:user_id, :symbol, :shares, :price)", user_id=session["user_id"], symbol=symbol, shares=shares, price=sharePrice)

        flash("Successfully bought!")

        return redirect("/")

    else:
        return render_template("buy.html")


@app.route("/history")
@login_required
def history():

    transactions = db.execute("SELECT symbol, shares, price, timestamp FROM purchases WHERE user_id = :user_id", user_id=session["user_id"])

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
            return apology("must provide username")

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password")

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username", username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")): 
            return apology("invalid username and/or password")

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""

    if request.method=="POST":
        quote=lookup(request.form.get("symbol"))
        
        if quote==None:
            return apology("Please enter a valid ticker symbol")
        return render_template("quoted.html", quote=quote)

    else:
        return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    #Reached route via POST (submitting form as post)
    if request.method == "POST":
        username=request.form.get("username")
        password=request.form.get("password")
        confirm_password=request.form.get("confirm-password")   
    
        #Make sure username isn't blank, else return apology message
        if username:
        
            #Make sure password isn't blank, else return apology message
            if password:
            
                #Check if password = confirm password, else return apology message
                if password==confirm_password:
                
                    #Generate a hash of password to be stored in database
                    passHash=generate_password_hash(password)
                
                    #Execute insert to find if the username exists within database. If it doesn't exist, db.execute will fail and return apology. Otherwise, adds to database
                    uniqueUsername=db.execute("INSERT INTO users (username, hash) VALUES(:username, :hash)", username=username, hash=passHash)      
                    if not uniqueUsername:
                              
                        return apology("Username is already in use. Please use a different username")
                    
                    # Remember which user has logged in
                    session["user_id"] = uniqueUsername

                    # Display a flash message
                    flash("Registered!")
                    
                    #redirect to login page
                    return redirect("/")
                return apology("Passwords do not match")
            return apology("Please fill in Password to continue")
        return apology("Please fill in Username to continue")


    #Reached route via GET (clicking link/redirect)
    else:
        return render_template("register.html")
    


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    #form: ticker, x shares

    #if reached via post
    if request.method == "POST":

        # check ticker
        stock = lookup (request.form.get("symbol"))
        if stock==None:
            return apology("Invalid ticker symbol")
        
        #check shares is a positive integer
        shares = request.form.get("shares")
        if not shares or not shares.isdigit() or float(shares)%1!=0 or int(shares)<1:
            return apology("The number of shares you wish to sell is not valid")
        
        shares = int (shares)
        #check user has at least x shares of that ticker in their current portfolio
        current_shares = db.execute("SELECT SUM(shares) AS total_shares FROM purchases WHERE user_id = :user_id AND symbol = :symbol GROUP BY symbol", user_id=session["user_id"], symbol=request.form.get("symbol"))
        
    
        if shares > current_shares[0]["total_shares"] or current_shares[0]["total_shares"] < 1:
            return apology("You do not have that many shares to sell")
              
             
        # update cash position & add -x shares from their portfolio 
        current_price = stock["price"]
        current_value = current_price * shares

        db.execute("UPDATE users SET cash = cash + :current_value WHERE id = :user_id", user_id = session["user_id"], current_value = current_value)
        db.execute("INSERT INTO purchases (user_id, symbol, shares, price) VALUES(:user_id, :symbol, :shares, :price)", user_id=session["user_id"], symbol=request.form.get("symbol"), shares=-shares, price=current_price)

        return redirect("/")
        

    else:
        available_stocks = db.execute("SELECT symbol, SUM(shares) as total_shares FROM purchases WHERE user_id = :user_id GROUP BY symbol", user_id=session["user_id"])
        return render_template("sell.html", available_stocks=available_stocks)
        

    return apology("TODO")


def errorhandler(e):
    """Handle error"""
    return apology(e.name, e.code)


# listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
