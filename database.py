import sqlite3
from datetime import datetime

DB_PATH = "brainrot.db"

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            telegram_id INTEGER UNIQUE NOT NULL,
            username TEXT,
            roblox_nick TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS listings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            brainrot_name TEXT NOT NULL,
            photo_id TEXT NOT NULL,
            bio TEXT,
            type TEXT NOT NULL DEFAULT 'sell',
            status TEXT NOT NULL DEFAULT 'active',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(telegram_id)
        )
    """)

    conn.commit()
    conn.close()

def register_user(telegram_id: int, username: str, roblox_nick: str):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        INSERT INTO users (telegram_id, username, roblox_nick)
        VALUES (?, ?, ?)
        ON CONFLICT(telegram_id) DO UPDATE SET
            username=excluded.username,
            roblox_nick=excluded.roblox_nick
    """, (telegram_id, username, roblox_nick))
    conn.commit()
    conn.close()

def get_user(telegram_id: int):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None

def add_listing(user_id: int, brainrot_name: str, photo_id: str, bio: str, type: str = "sell"):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        INSERT INTO listings (user_id, brainrot_name, photo_id, bio, type)
        VALUES (?, ?, ?, ?, ?)
    """, (user_id, brainrot_name, photo_id, bio, type))
    listing_id = c.lastrowid
    conn.commit()
    conn.close()
    return listing_id

def get_listings(type: str = "sell", status: str = "active"):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        SELECT l.*, u.username, u.roblox_nick
        FROM listings l
        JOIN users u ON l.user_id = u.telegram_id
        WHERE l.type = ? AND l.status = ?
        ORDER BY l.created_at DESC
    """, (type, status))
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_user_listings(user_id: int):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        SELECT * FROM listings
        WHERE user_id = ? AND status = 'active'
        ORDER BY created_at DESC
    """, (user_id,))
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def delete_listing(listing_id: int, user_id: int):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        UPDATE listings SET status = 'deleted'
        WHERE id = ? AND user_id = ?
    """, (listing_id, user_id))
    conn.commit()
    conn.close()

def get_all_users():
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM users ORDER BY created_at DESC")
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]
