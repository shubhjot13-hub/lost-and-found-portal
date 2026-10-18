import os
import sqlite3
from datetime import date
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, session, abort
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, "portal.db")
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-development-secret")
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

CATEGORIES = ["Electronics", "Bags", "Documents", "Keys", "Clothing", "Accessories", "Books", "Other"]

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    with get_db() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            category TEXT NOT NULL,
            report_type TEXT NOT NULL CHECK(report_type IN ('Lost', 'Found')),
            location TEXT NOT NULL,
            item_date TEXT NOT NULL,
            image_filename TEXT,
            contact_info TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Open' CHECK(status IN ('Open', 'Resolved')),
            user_id INTEGER NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        """)
init_db()

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def current_user():
    if "user_id" not in session:
        return None
    with get_db() as db:
        return db.execute("SELECT id, name, email FROM users WHERE id = ?", (session["user_id"],)).fetchone()

def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user():
            flash("Please log in to continue.", "info")
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)
    return wrapped

@app.context_processor
def inject_globals():
    return {"current_user": current_user(), "categories": CATEGORIES}

@app.route("/")
def index():
    search = request.args.get("q", "").strip()
    category = request.args.get("category", "").strip()
    report_type = request.args.get("type", "").strip()
    location = request.args.get("location", "").strip()
    conditions = ["items.status = 'Open'"]
    params = []
    if search:
        conditions.append("(items.title LIKE ? OR items.description LIKE ?)")
        params.extend([f"%{search}%", f"%{search}%"])
    if category in CATEGORIES:
        conditions.append("items.category = ?")
        params.append(category)
    if report_type in ("Lost", "Found"):
        conditions.append("items.report_type = ?")
        params.append(report_type)
    if location:
        conditions.append("items.location LIKE ?")
        params.append(f"%{location}%")
    where = " WHERE " + " AND ".join(conditions)
    with get_db() as db:
        items = db.execute(
            "SELECT items.*, users.name AS reporter FROM items JOIN users ON users.id=items.user_id" +
            where + " ORDER BY items.created_at DESC", params
        ).fetchall()
        stats = {
            "total": db.execute("SELECT COUNT(*) FROM items").fetchone()[0],
            "lost": db.execute("SELECT COUNT(*) FROM items WHERE report_type='Lost' AND status='Open'").fetchone()[0],
            "found": db.execute("SELECT COUNT(*) FROM items WHERE report_type='Found' AND status='Open'").fetchone()[0],
            "resolved": db.execute("SELECT COUNT(*) FROM items WHERE status='Resolved'").fetchone()[0],
        }
    return render_template("index.html", items=items, stats=stats, filters={
        "q": search, "category": category, "type": report_type, "location": location
    })

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        if not name or not email or len(password) < 8:
            flash("Enter your name, a valid email, and a password of at least 8 characters.", "error")
            return render_template("register.html")
        try:
            with get_db() as db:
                cur = db.execute("INSERT INTO users(name,email,password_hash) VALUES(?,?,?)",
                                 (name, email, generate_password_hash(password)))
                session["user_id"] = cur.lastrowid
            flash("Your account has been created. Welcome!", "success")
            return redirect(url_for("index"))
        except sqlite3.IntegrityError:
            flash("An account with that email already exists.", "error")
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        with get_db() as db:
            user = db.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["user_id"] = user["id"]
            flash("You are now logged in.", "success")
            return redirect(request.args.get("next") or url_for("index"))
        flash("Email or password is incorrect.", "error")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("index"))

@app.route("/report", methods=["GET", "POST"])
@login_required
def report():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        category = request.form.get("category", "")
        report_type = request.form.get("report_type", "")
        location = request.form.get("location", "").strip()
        item_date = request.form.get("item_date", "")
        contact_info = request.form.get("contact_info", "").strip()
        image = request.files.get("image")
        if not all([title, description, category in CATEGORIES, report_type in ("Lost", "Found"),
                    location, item_date, contact_info]):
            flash("Please complete all required fields.", "error")
            return render_template("report.html", today=date.today().isoformat())
        image_filename = None
        if image and image.filename:
            if not allowed_file(image.filename):
                flash("Image must be PNG, JPG, JPEG, GIF, or WEBP.", "error")
                return render_template("report.html", today=date.today().isoformat())
            safe_name = secure_filename(image.filename)
            image_filename = f"{session['user_id']}_{os.urandom(6).hex()}_{safe_name}"
            image.save(os.path.join(UPLOAD_FOLDER, image_filename))
        with get_db() as db:
            db.execute("""INSERT INTO items(title,description,category,report_type,location,item_date,
                          image_filename,contact_info,user_id) VALUES(?,?,?,?,?,?,?,?,?)""",
                       (title, description, category, report_type, location, item_date,
                        image_filename, contact_info, session["user_id"]))
        flash("Your item report has been published.", "success")
        return redirect(url_for("my_reports"))
    return render_template("report.html", today=date.today().isoformat())

@app.route("/item/<int:item_id>")
def item_detail(item_id):
    with get_db() as db:
        item = db.execute("""SELECT items.*, users.name AS reporter FROM items
                             JOIN users ON users.id=items.user_id WHERE items.id=?""",
                          (item_id,)).fetchone()
    if not item:
        abort(404)
    return render_template("item_detail.html", item=item)

@app.route("/my-reports")
@login_required
def my_reports():
    with get_db() as db:
        items = db.execute("SELECT * FROM items WHERE user_id=? ORDER BY created_at DESC",
                           (session["user_id"],)).fetchall()
    return render_template("my_reports.html", items=items)

@app.route("/item/<int:item_id>/resolve", methods=["POST"])
@login_required
def resolve_item(item_id):
    with get_db() as db:
        item = db.execute("SELECT user_id FROM items WHERE id=?", (item_id,)).fetchone()
        if not item:
            abort(404)
        if item["user_id"] != session["user_id"]:
            abort(403)
        db.execute("UPDATE items SET status='Resolved' WHERE id=?", (item_id,))
    flash("Report marked as resolved.", "success")
    return redirect(url_for("my_reports"))

@app.route("/item/<int:item_id>/delete", methods=["POST"])
@login_required
def delete_item(item_id):
    with get_db() as db:
        item = db.execute("SELECT * FROM items WHERE id=?", (item_id,)).fetchone()
        if not item:
            abort(404)
        if item["user_id"] != session["user_id"]:
            abort(403)
        if item["image_filename"]:
            try:
                os.remove(os.path.join(UPLOAD_FOLDER, item["image_filename"]))
            except OSError:
                pass
        db.execute("DELETE FROM items WHERE id=?", (item_id,))
    flash("Report deleted.", "success")
    return redirect(url_for("my_reports"))

@app.errorhandler(413)
def too_large(_error):
    flash("Image is too large. Please choose an image smaller than 5 MB.", "error")
    return redirect(url_for("report"))

if __name__ == "__main__":
    app.run(debug=True)
