import os
import secrets
import sqlite3
import hashlib
from datetime import datetime, timedelta, timezone
from functools import wraps

from flask import Flask, request, jsonify, g
from flask_cors import CORS

APP = Flask(__name__)
CORS(APP)

DB_PATH = os.getenv("FIXBAN_DB", "fix_ban.db")
SECRET = os.getenv("FIXBAN_SECRET", "CHANGE_THIS_SECRET_IN_PRODUCTION")
TOKEN_HOURS = int(os.getenv("FIXBAN_TOKEN_HOURS", "24"))

def now():
    return datetime.now(timezone.utc).isoformat()

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db

@APP.teardown_appcontext
def close_db(_error=None):
    db = g.pop("db", None)
    if db:
        db.close()

def init_db():
    db = sqlite3.connect(DB_PATH)
    db.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'user',
        created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS people (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        first_name TEXT NOT NULL,
        last_name TEXT NOT NULL,
        age INTEGER NOT NULL,
        birth_date TEXT NOT NULL,
        phone TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS sessions (
        token TEXT PRIMARY KEY,
        user_id INTEGER NOT NULL,
        expires_at TEXT NOT NULL
    );
    """)
    admin = db.execute("SELECT id FROM users WHERE username='admin'").fetchone()
    if not admin:
        db.execute(
            "INSERT INTO users(username,password_hash,role,created_at) VALUES(?,?,?,?)",
            ("admin", hash_password("Admin@123"), "admin", now())
        )
    db.commit()
    db.close()

def hash_password(password):
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 180000)
    return salt.hex() + "$" + digest.hex()

def verify_password(password, stored):
    try:
        salt_hex, digest_hex = stored.split("$", 1)
        salt = bytes.fromhex(salt_hex)
        digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 180000)
        return secrets.compare_digest(digest.hex(), digest_hex)
    except Exception:
        return False

def make_token():
    return secrets.token_urlsafe(48)

def auth_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        token = request.headers.get("Authorization", "")
        if token.startswith("Bearer "):
            token = token[7:]
        if not token:
            return jsonify(ok=False, error="Authentication required."), 401

        db = get_db()
        row = db.execute("""
            SELECT s.token, s.expires_at, u.id, u.username, u.role
            FROM sessions s JOIN users u ON u.id=s.user_id
            WHERE s.token=?
        """, (token,)).fetchone()

        if not row:
            return jsonify(ok=False, error="Invalid session."), 401

        if datetime.fromisoformat(row["expires_at"]) < datetime.now(timezone.utc):
            db.execute("DELETE FROM sessions WHERE token=?", (token,))
            db.commit()
            return jsonify(ok=False, error="Session expired."), 401

        g.user = dict(row)
        return fn(*args, **kwargs)
    return wrapper

def admin_required(fn):
    @wraps(fn)
    @auth_required
    def wrapper(*args, **kwargs):
        if g.user["role"] != "admin":
            return jsonify(ok=False, error="Admin access required."), 403
        return fn(*args, **kwargs)
    return wrapper

@APP.get("/api/health")
def health():
    return jsonify(ok=True, app="F!X BAN", status="online")

@APP.post("/api/login")
def login():
    data = request.get_json(silent=True) or {}
    username = str(data.get("username", "")).strip()
    password = str(data.get("password", ""))

    db = get_db()
    user = db.execute(
        "SELECT id,username,password_hash,role FROM users WHERE username=?",
        (username,)
    ).fetchone()

    if not user or not verify_password(password, user["password_hash"]):
        return jsonify(ok=False, error="Invalid username or password."), 401

    token = make_token()
    expires = datetime.now(timezone.utc) + timedelta(hours=TOKEN_HOURS)
    db.execute(
        "INSERT INTO sessions(token,user_id,expires_at) VALUES(?,?,?)",
        (token, user["id"], expires.isoformat())
    )
    db.commit()

    return jsonify(
        ok=True,
        token=token,
        user={"id": user["id"], "username": user["username"], "role": user["role"]}
    )

@APP.post("/api/logout")
@auth_required
def logout():
    token = request.headers.get("Authorization", "")[7:]
    db = get_db()
    db.execute("DELETE FROM sessions WHERE token=?", (token,))
    db.commit()
    return jsonify(ok=True)

@APP.get("/api/me")
@auth_required
def me():
    return jsonify(ok=True, user={
        "id": g.user["id"], "username": g.user["username"], "role": g.user["role"]
    })

@APP.get("/api/people")
@auth_required
def list_people():
    db = get_db()
    rows = db.execute("""
        SELECT id,first_name,last_name,age,birth_date,phone,created_at,updated_at
        FROM people ORDER BY id DESC
    """).fetchall()
    return jsonify(ok=True, people=[dict(r) for r in rows])

def validate_person(data):
    fields = ["first_name", "last_name", "age", "birth_date", "phone"]
    if any(not str(data.get(x, "")).strip() for x in fields):
        return None, "All person fields are required."
    try:
        age = int(data["age"])
        if age < 0 or age > 150:
            return None, "Age must be between 0 and 150."
    except Exception:
        return None, "Age must be a valid number."
    return {
        "first_name": str(data["first_name"]).strip(),
        "last_name": str(data["last_name"]).strip(),
        "age": age,
        "birth_date": str(data["birth_date"]).strip(),
        "phone": str(data["phone"]).strip()
    }, None

@APP.post("/api/people")
@admin_required
def add_person():
    person, error = validate_person(request.get_json(silent=True) or {})
    if error:
        return jsonify(ok=False, error=error), 400
    db = get_db()
    stamp = now()
    cur = db.execute("""
        INSERT INTO people(first_name,last_name,age,birth_date,phone,created_at,updated_at)
        VALUES(?,?,?,?,?,?,?)
    """, (person["first_name"], person["last_name"], person["age"],
          person["birth_date"], person["phone"], stamp, stamp))
    db.commit()
    person["id"] = cur.lastrowid
    person["created_at"] = stamp
    person["updated_at"] = stamp
    return jsonify(ok=True, person=person), 201

@APP.put("/api/people/<int:person_id>")
@admin_required
def update_person(person_id):
    person, error = validate_person(request.get_json(silent=True) or {})
    if error:
        return jsonify(ok=False, error=error), 400
    db = get_db()
    stamp = now()
    cur = db.execute("""
        UPDATE people
        SET first_name=?,last_name=?,age=?,birth_date=?,phone=?,updated_at=?
        WHERE id=?
    """, (person["first_name"], person["last_name"], person["age"],
          person["birth_date"], person["phone"], stamp, person_id))
    db.commit()
    if cur.rowcount == 0:
        return jsonify(ok=False, error="Person not found."), 404
    return jsonify(ok=True)

@APP.delete("/api/people/<int:person_id>")
@admin_required
def delete_person(person_id):
    db = get_db()
    cur = db.execute("DELETE FROM people WHERE id=?", (person_id,))
    db.commit()
    if cur.rowcount == 0:
        return jsonify(ok=False, error="Person not found."), 404
    return jsonify(ok=True)

@APP.get("/api/users")
@admin_required
def list_users():
    db = get_db()
    rows = db.execute(
        "SELECT id,username,role,created_at FROM users ORDER BY id DESC"
    ).fetchall()
    return jsonify(ok=True, users=[dict(r) for r in rows])

@APP.post("/api/users")
@admin_required
def create_user():
    data = request.get_json(silent=True) or {}
    username = str(data.get("username", "")).strip()
    password = str(data.get("password", ""))
    role = data.get("role", "user")
    if not username or len(password) < 6 or role not in ("user", "admin"):
        return jsonify(ok=False, error="Username, password (6+ characters), and role are required."), 400

    db = get_db()
    try:
        db.execute(
            "INSERT INTO users(username,password_hash,role,created_at) VALUES(?,?,?,?)",
            (username, hash_password(password), role, now())
        )
        db.commit()
    except sqlite3.IntegrityError:
        return jsonify(ok=False, error="Username already exists."), 409
    return jsonify(ok=True)

@APP.patch("/api/users/<int:user_id>/role")
@admin_required
def change_role(user_id):
    data = request.get_json(silent=True) or {}
    role = data.get("role")
    if role not in ("user", "admin"):
        return jsonify(ok=False, error="Invalid role."), 400
    if user_id == g.user["id"] and role != "admin":
        return jsonify(ok=False, error="You cannot remove your own admin access."), 400

    db = get_db()
    cur = db.execute("UPDATE users SET role=? WHERE id=?", (role, user_id))
    db.commit()
    if cur.rowcount == 0:
        return jsonify(ok=False, error="User not found."), 404
    return jsonify(ok=True)

@APP.delete("/api/users/<int:user_id>")
@admin_required
def delete_user(user_id):
    if user_id == g.user["id"]:
        return jsonify(ok=False, error="You cannot delete your own account."), 400
    db = get_db()
    cur = db.execute("DELETE FROM users WHERE id=?", (user_id,))
    db.commit()
    if cur.rowcount == 0:
        return jsonify(ok=False, error="User not found."), 404
    return jsonify(ok=True)

if __name__ == "__main__":
    init_db()
    port = int(os.getenv("PORT", "8000"))
    APP.run(host="0.0.0.0", port=port)
else:
    init_db()
