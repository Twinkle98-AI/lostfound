import sqlite3
import os
from dotenv import load_dotenv

load_dotenv()
DB_PATH = os.getenv("DB_PATH", "lost_found.db")


# ─────────────────────────── DB INIT ────────────────────────────

def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            username   TEXT UNIQUE NOT NULL,
            password   TEXT NOT NULL,
            email      TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS items (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL,
            title       TEXT NOT NULL,
            type        TEXT NOT NULL CHECK(type IN ('Lost','Found')),
            location    TEXT,
            date        TEXT,
            description TEXT,
            image_url   TEXT,
            status      TEXT DEFAULT 'open',
            created_at  TEXT DEFAULT (datetime('now')),
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id   INTEGER NOT NULL,
            receiver_id INTEGER NOT NULL,
            content     TEXT NOT NULL,
            is_read     INTEGER DEFAULT 0,
            created_at  TEXT DEFAULT (datetime('now')),
            FOREIGN KEY(sender_id)   REFERENCES users(id),
            FOREIGN KEY(receiver_id) REFERENCES users(id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    INTEGER NOT NULL,
            type       TEXT,
            title      TEXT,
            message    TEXT,
            item_id    INTEGER,
            is_read    INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)

    conn.commit()
    conn.close()


# ─────────────────────────── USERS ──────────────────────────────

def register_user(username, password, email=""):
    conn = get_conn()
    try:
        conn.execute(
            "INSERT INTO users (username, password, email) VALUES (?,?,?)",
            (username, password, email)
        )
        conn.commit()
        return True, "Registered successfully!"
    except sqlite3.IntegrityError:
        return False, "Username already exists."
    finally:
        conn.close()


def login_user(username, password):
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM users WHERE username=? AND password=?",
        (username, password)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


# ─────────────────────────── ITEMS ──────────────────────────────

def create_item(user_id, title, item_type, location, date, description, image_url=""):
    conn = get_conn()
    conn.execute(
        """INSERT INTO items (user_id,title,type,location,date,description,image_url)
           VALUES (?,?,?,?,?,?,?)""",
        (user_id, title, item_type, location, date, description, image_url)
    )
    conn.commit()
    conn.close()


def get_all_items(filter_type="All", search=""):
    conn = get_conn()
    query = """
        SELECT i.*, u.username
        FROM items i
        JOIN users u ON i.user_id = u.id
        WHERE i.status = 'open'
    """
    params = []
    if filter_type != "All":
        query += " AND i.type = ?"
        params.append(filter_type)
    if search:
        query += " AND (i.title LIKE ? OR i.description LIKE ? OR i.location LIKE ?)"
        params += [f"%{search}%", f"%{search}%", f"%{search}%"]
    query += " ORDER BY i.created_at DESC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_item_by_id(item_id):
    conn = get_conn()
    row = conn.execute(
        "SELECT i.*, u.username FROM items i JOIN users u ON i.user_id=u.id WHERE i.id=?",
        (item_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_user_items(user_id):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM items WHERE user_id=? ORDER BY created_at DESC",
        (user_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def mark_item_resolved(item_id):
    conn = get_conn()
    conn.execute("UPDATE items SET status='resolved' WHERE id=?", (item_id,))
    conn.commit()
    conn.close()


def delete_item(item_id):
    conn = get_conn()
    conn.execute("DELETE FROM items WHERE id=?", (item_id,))
    conn.commit()
    conn.close()


# ─────────────────────────── MESSAGES ───────────────────────────

def send_message(sender_id, receiver_id, content):
    conn = get_conn()
    conn.execute(
        "INSERT INTO messages (sender_id, receiver_id, content) VALUES (?,?,?)",
        (sender_id, receiver_id, content)
    )
    conn.commit()
    conn.close()


def get_conversations(user_id):
    conn = get_conn()
    rows = conn.execute("""
        SELECT DISTINCT
            CASE WHEN sender_id=? THEN receiver_id ELSE sender_id END AS partner_id,
            u.username AS partner_name,
            MAX(m.created_at) AS last_msg_time
        FROM messages m
        JOIN users u ON u.id = CASE WHEN m.sender_id=? THEN m.receiver_id ELSE m.sender_id END
        WHERE m.sender_id=? OR m.receiver_id=?
        GROUP BY partner_id
        ORDER BY last_msg_time DESC
    """, (user_id, user_id, user_id, user_id)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_messages_between(user_id, partner_id):
    conn = get_conn()
    rows = conn.execute("""
        SELECT m.*, u.username AS sender_name
        FROM messages m
        JOIN users u ON u.id = m.sender_id
        WHERE (sender_id=? AND receiver_id=?) OR (sender_id=? AND receiver_id=?)
        ORDER BY m.created_at ASC
    """, (user_id, partner_id, partner_id, user_id)).fetchall()
    conn.execute(
        "UPDATE messages SET is_read=1 WHERE sender_id=? AND receiver_id=?",
        (partner_id, user_id)
    )
    conn.commit()
    conn.close()
    return [dict(r) for r in rows]


def get_unread_message_count(user_id):
    conn = get_conn()
    count = conn.execute(
        "SELECT COUNT(*) FROM messages WHERE receiver_id=? AND is_read=0",
        (user_id,)
    ).fetchone()[0]
    conn.close()
    return count


# ─────────────────────────── NOTIFICATIONS ──────────────────────

def create_notification(user_id, notif_type, title, message, item_id=None):
    conn = get_conn()
    conn.execute(
        "INSERT INTO notifications (user_id, type, title, message, item_id) VALUES (?,?,?,?,?)",
        (user_id, notif_type, title, message, item_id)
    )
    conn.commit()
    conn.close()


def get_notifications(user_id):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM notifications WHERE user_id=? ORDER BY created_at DESC LIMIT 50",
        (user_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_unread_notification_count(user_id):
    conn = get_conn()
    count = conn.execute(
        "SELECT COUNT(*) FROM notifications WHERE user_id=? AND is_read=0",
        (user_id,)
    ).fetchone()[0]
    conn.close()
    return count


def mark_notifications_read(user_id):
    conn = get_conn()
    conn.execute("UPDATE notifications SET is_read=1 WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()


# ─────────────────────────── CLOUDINARY ─────────────────────────

def upload_image(file_bytes, filename="upload"):
    try:
        import cloudinary
        import cloudinary.uploader
        cloudinary.config(
            cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
            api_key=os.getenv("CLOUDINARY_API_KEY"),
            api_secret=os.getenv("CLOUDINARY_API_SECRET"),
        )
        result = cloudinary.uploader.upload(file_bytes, public_id=filename)
        return result.get("secure_url", "")
    except Exception as e:
        print(f"[Cloudinary] Upload failed: {e}")
        return ""
