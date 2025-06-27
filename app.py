import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, flash, g
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "change_this_to_a_random_secret"

DATABASE = "instance/passwords.db"

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    with app.app_context():
        db = get_db()
        db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )""")
        db.execute("""
        CREATE TABLE IF NOT EXISTS passwords (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            site TEXT NOT NULL,
            login TEXT NOT NULL,
            password TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )""")
        db.commit()

@app.route("/")
def index():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return render_template("index.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = generate_password_hash(request.form["password"])
        db = get_db()
        try:
            db.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
            db.commit()
            flash("Registration successful! Please log in.", "success")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("Username already exists.", "danger")
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        db = get_db()
        user = db.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            flash("Logged in successfully!", "success")
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid credentials.", "danger")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out.", "info")
    return redirect(url_for("index"))

@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))
    db = get_db()
    passwords = db.execute(
        "SELECT * FROM passwords WHERE user_id = ?", (session["user_id"],)
    ).fetchall()
    return render_template("dashboard.html", passwords=passwords)

@app.route("/add", methods=["GET", "POST"])
def add():
    if "user_id" not in session:
        return redirect(url_for("login"))
    if request.method == "POST":
        site = request.form["site"]
        login_name = request.form["login"]
        password = request.form["password"]
        db = get_db()
        db.execute(
            "INSERT INTO passwords (user_id, site, login, password) VALUES (?, ?, ?, ?)",
            (session["user_id"], site, login_name, password)
        )
        db.commit()
        flash("Password added!", "success")
        return redirect(url_for("dashboard"))
    return render_template("add.html")

@app.route("/edit/<int:id>", methods=["GET", "POST"])
def edit(id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    db = get_db()
    pw = db.execute(
        "SELECT * FROM passwords WHERE id = ? AND user_id = ?", (id, session["user_id"])
    ).fetchone()
    if not pw:
        flash("Not found.", "danger")
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        site = request.form["site"]
        login_name = request.form["login"]
        password = request.form["password"]
        db.execute(
            "UPDATE passwords SET site = ?, login = ?, password = ? WHERE id = ?",
            (site, login_name, password, id)
        )
        db.commit()
        flash("Password updated.", "success")
        return redirect(url_for("dashboard"))
    return render_template("edit.html", pw=pw)

@app.route("/delete/<int:id>")
def delete(id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    db = get_db()
    db.execute(
        "DELETE FROM passwords WHERE id = ? AND user_id = ?", (id, session["user_id"])
    )
    db.commit()
    flash("Deleted.", "info")
    return redirect(url_for("dashboard"))

if __name__ == "__main__":
    init_db()
    app.run(debug=True)