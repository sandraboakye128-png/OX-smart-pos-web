import sqlite3
import hashlib
import os

# ---------- Ensure database folder exists ----------
DB_DIR = "database"
os.makedirs(DB_DIR, exist_ok=True)
DB_PATH = os.path.join(DB_DIR, "auth.db")  # Separate auth DB

# ---------------- INIT DATABASE ----------------
def init_auth_db():
    """Create users table if it doesn't exist."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('admin', 'user')),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    conn.commit()
    conn.close()


# ---------------- HASH PASSWORD ----------------
def hash_password(password: str) -> str:
    """Return a SHA-256 hash of the password."""
    return hashlib.sha256(password.encode()).hexdigest()


# ---------------- CREATE USER ----------------
def create_user(username: str, password: str, role: str = "user") -> bool:
    """Create a new user. Returns True if successful, False if username exists."""
    init_auth_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
            (username, hash_password(password), role)
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


# ---------------- LOGIN USER ----------------
def login_user(username: str, password: str):
    """Return user dict if credentials are correct, else None."""
    init_auth_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id, username, role, password FROM users WHERE username=?",
        (username,)
    )
    user = cursor.fetchone()
    conn.close()

    if user and user[3] == hash_password(password):
        return {"id": user[0], "username": user[1], "role": user[2]}
    return None


# ---------------- CHECK ADMIN EXISTS ----------------
def admin_exists() -> bool:
    """Return True if an admin user exists."""
    init_auth_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT 1 FROM users WHERE role='admin' LIMIT 1")
    exists = cursor.fetchone() is not None
    conn.close()
    return exists