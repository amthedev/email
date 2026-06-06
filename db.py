import sqlite3
from contextlib import contextmanager

DB_PATH = "email.db"


def init_db():
    with get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS accounts (
                id          TEXT PRIMARY KEY,
                address     TEXT UNIQUE NOT NULL,
                password    TEXT NOT NULL,
                token       TEXT,
                provider    TEXT DEFAULT 'mailtm',
                created_at  TEXT DEFAULT (datetime('now')),
                label       TEXT DEFAULT '',
                note        TEXT DEFAULT ''
            );


            CREATE TABLE IF NOT EXISTS messages (
                id          TEXT PRIMARY KEY,
                account_id  TEXT NOT NULL,
                from_addr   TEXT,
                subject     TEXT,
                body        TEXT,
                received_at TEXT,
                seen        INTEGER DEFAULT 0,
                FOREIGN KEY (account_id) REFERENCES accounts(id)
            );

            CREATE INDEX IF NOT EXISTS idx_messages_account ON messages(account_id);
            CREATE INDEX IF NOT EXISTS idx_messages_seen    ON messages(seen);
            CREATE INDEX IF NOT EXISTS idx_accounts_address ON accounts(address);
        """)
        # migrate existing DBs without provider column
        try:
            conn.execute("ALTER TABLE accounts ADD COLUMN provider TEXT DEFAULT 'mailtm'")
        except Exception:
            pass


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


# --- accounts ---

def save_account(acc: dict):
    with get_conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO accounts (id, address, password, token, provider) VALUES (?,?,?,?,?)",
            (acc["id"], acc["address"], acc["password"], acc.get("token", ""), acc.get("provider", "mailtm"))
        )


def update_token(account_id: str, token: str):
    with get_conn() as conn:
        conn.execute("UPDATE accounts SET token=? WHERE id=?", (token, account_id))


def update_label(account_id: str, label: str, note: str):
    with get_conn() as conn:
        conn.execute("UPDATE accounts SET label=?, note=? WHERE id=?", (label, note, account_id))


def delete_account_db(account_id: str):
    with get_conn() as conn:
        conn.execute("DELETE FROM messages WHERE account_id=?", (account_id,))
        conn.execute("DELETE FROM accounts WHERE id=?", (account_id,))


def get_all_accounts():
    with get_conn() as conn:
        return conn.execute("""
            SELECT a.*,
                   COUNT(m.id)                          AS total_msgs,
                   SUM(CASE WHEN m.seen=0 THEN 1 ELSE 0 END) AS unread
            FROM accounts a
            LEFT JOIN messages m ON m.account_id = a.id
            GROUP BY a.id
            ORDER BY a.created_at DESC
        """).fetchall()


def search_accounts(q: str):
    like = f"%{q}%"
    with get_conn() as conn:
        return conn.execute("""
            SELECT a.*,
                   COUNT(m.id)                               AS total_msgs,
                   SUM(CASE WHEN m.seen=0 THEN 1 ELSE 0 END) AS unread
            FROM accounts a
            LEFT JOIN messages m ON m.account_id = a.id
            WHERE a.address LIKE ? OR a.label LIKE ? OR a.note LIKE ?
            GROUP BY a.id
            ORDER BY a.created_at DESC
        """, (like, like, like)).fetchall()


def get_account(account_id: str):
    with get_conn() as conn:
        return conn.execute("SELECT * FROM accounts WHERE id=?", (account_id,)).fetchone()


# --- messages ---

def save_messages(account_id: str, msgs: list):
    with get_conn() as conn:
        for m in msgs:
            conn.execute("""
                INSERT OR IGNORE INTO messages (id, account_id, from_addr, subject, body, received_at)
                VALUES (?,?,?,?,?,?)
            """, (
                m["id"], account_id,
                m.get("from", {}).get("address", ""),
                m.get("subject", ""),
                m.get("text") or m.get("intro", ""),
                m.get("createdAt", "")
            ))


def save_full_message(account_id: str, msg: dict):
    with get_conn() as conn:
        conn.execute("""
            INSERT OR REPLACE INTO messages (id, account_id, from_addr, subject, body, received_at, seen)
            VALUES (?,?,?,?,?,?,1)
        """, (
            msg["id"], account_id,
            msg.get("from", {}).get("address", ""),
            msg.get("subject", ""),
            msg.get("text") or msg.get("html", ""),
            msg.get("createdAt", "")
        ))


def get_messages(account_id: str):
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM messages WHERE account_id=? ORDER BY received_at DESC",
            (account_id,)
        ).fetchall()


def search_messages(q: str):
    like = f"%{q}%"
    with get_conn() as conn:
        return conn.execute("""
            SELECT m.*, a.address AS account_address
            FROM messages m
            JOIN accounts a ON a.id = m.account_id
            WHERE m.subject LIKE ? OR m.from_addr LIKE ? OR m.body LIKE ?
            ORDER BY m.received_at DESC
            LIMIT 100
        """, (like, like, like)).fetchall()


def mark_seen(message_id: str):
    with get_conn() as conn:
        conn.execute("UPDATE messages SET seen=1 WHERE id=?", (message_id,))


def delete_message_db(message_id: str):
    with get_conn() as conn:
        conn.execute("DELETE FROM messages WHERE id=?", (message_id,))


def stats():
    with get_conn() as conn:
        row = conn.execute("""
            SELECT
                (SELECT COUNT(*) FROM accounts)                     AS total_accounts,
                (SELECT COUNT(*) FROM messages)                     AS total_messages,
                (SELECT COUNT(*) FROM messages WHERE seen=0)        AS unread,
                (SELECT COUNT(*) FROM messages WHERE date(received_at)=date('now')) AS today
        """).fetchone()
        return dict(row)
