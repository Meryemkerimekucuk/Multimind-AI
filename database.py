import sqlite3, hashlib, secrets, hmac
from datetime import datetime

DATABASE_NAME = str(__import__("pathlib").Path(__file__).resolve().parent / "chats.db")


def get_connection():
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _password_hash(password, salt):
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 310000).hex()


def create_user(username, password):
    username = username.strip().lower()
    salt = secrets.token_hex(16)
    hashed = _password_hash(password, salt)
    with get_connection() as conn:
        try:
            cur = conn.execute("INSERT INTO users (username, salt, password_hash, created_at) VALUES (?, ?, ?, ?)",
                             (username, salt, hashed, datetime.now().isoformat()))
            return cur.lastrowid
        except sqlite3.IntegrityError:
            return None



def authenticate_user(username, password):
    with get_connection() as conn:
        row = conn.execute("SELECT id, username, salt, password_hash FROM users WHERE username = ?", (username.strip().lower(),)).fetchone()
    if not row or not hmac.compare_digest(_password_hash(password, row["salt"]), row["password_hash"]):
        return None
    return {"id": row["id"], "username": row["username"]}



def init_database():
    with get_connection() as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL, salt TEXT NOT NULL, password_hash TEXT NOT NULL, created_at TEXT NOT NULL)")
        conn.execute("CREATE TABLE IF NOT EXISTS chats (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, created_at TEXT NOT NULL, owner_id INTEGER)")
        conn.execute("CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id INTEGER NOT NULL, role TEXT NOT NULL, content TEXT NOT NULL, created_at TEXT NOT NULL, attachment_path TEXT, attachment_name TEXT, attachment_type TEXT, attachment_json TEXT, FOREIGN KEY(chat_id) REFERENCES chats(id) ON DELETE CASCADE)")
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(chats)").fetchall()}
        if "owner_id" not in cols:
            conn.execute("ALTER TABLE chats ADD COLUMN owner_id INTEGER")
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(messages)").fetchall()}
        for col, sql in {
            "attachment_path": "ALTER TABLE messages ADD COLUMN attachment_path TEXT",
            "attachment_name": "ALTER TABLE messages ADD COLUMN attachment_name TEXT",
            "attachment_type": "ALTER TABLE messages ADD COLUMN attachment_type TEXT",
            "attachment_json": "ALTER TABLE messages ADD COLUMN attachment_json TEXT",
        }.items():
            if col not in cols: conn.execute(sql)


def create_chat(name, owner_id):
    with get_connection() as conn:
        cur = conn.execute("INSERT INTO chats (name, created_at, owner_id) VALUES (?, ?, ?)", (name, datetime.now().isoformat(), owner_id))
        return cur.lastrowid


def get_all_chats(owner_id):
    with get_connection() as conn:
        return conn.execute("SELECT id, name, created_at FROM chats WHERE owner_id = ? ORDER BY id DESC", (owner_id,)).fetchall()


def get_messages(chat_id, owner_id):
    with get_connection() as conn:
        owns = conn.execute("SELECT 1 FROM chats WHERE id=? AND owner_id=?", (chat_id, owner_id)).fetchone()
        if not owns: return []
        return conn.execute("SELECT role, content, created_at, attachment_path, attachment_name, attachment_type, attachment_json FROM messages WHERE chat_id=? ORDER BY id ASC", (chat_id,)).fetchall()


def add_message(chat_id, owner_id, role, content, attachment_path=None, attachment_name=None, attachment_type=None, attachment_json=None):
    with get_connection() as conn:
        owns = conn.execute("SELECT 1 FROM chats WHERE id=? AND owner_id=?", (chat_id, owner_id)).fetchone()
        if not owns: raise PermissionError("Bu sohbet bu kullanıcıya ait değil.")
        conn.execute("INSERT INTO messages (chat_id, role, content, created_at, attachment_path, attachment_name, attachment_type, attachment_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (chat_id, role, content, datetime.now().isoformat(), attachment_path, attachment_name, attachment_type, attachment_json))


def rename_chat(chat_id, owner_id, new_name):
    with get_connection() as conn: conn.execute("UPDATE chats SET name=? WHERE id=? AND owner_id=?", (new_name, chat_id, owner_id))


def delete_chat(chat_id, owner_id):
    with get_connection() as conn:
        conn.execute("DELETE FROM messages WHERE chat_id=? AND chat_id IN (SELECT id FROM chats WHERE id=? AND owner_id=?)", (chat_id, chat_id, owner_id))
        conn.execute("DELETE FROM chats WHERE id=? AND owner_id=?", (chat_id, owner_id))
