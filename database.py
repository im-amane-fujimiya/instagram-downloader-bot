import sqlite3
import os
from contextlib import closing


DB_PATH = os.environ.get(
    "DATABASE_PATH",
    "bot.db"
)


def get_connection():
    conn = sqlite3.connect(
        DB_PATH,
        timeout=30
    )

    conn.row_factory = sqlite3.Row

    return conn


def init_database():

    with closing(get_connection()) as conn:

        conn.execute("""
            CREATE TABLE IF NOT EXISTS chats (
                chat_id TEXT PRIMARY KEY,
                chat_type TEXT NOT NULL,
                title TEXT DEFAULT '',
                active INTEGER DEFAULT 1
            )
        """)

        conn.commit()


def save_chat(
    chat_id,
    chat_type,
    title=""
):

    with closing(get_connection()) as conn:

        conn.execute("""
            INSERT INTO chats
            (chat_id, chat_type, title, active)
            VALUES (?, ?, ?, 1)

            ON CONFLICT(chat_id)
            DO UPDATE SET
                chat_type = excluded.chat_type,
                title = excluded.title,
                active = 1
        """, (
            str(chat_id),
            chat_type,
            title or ""
        ))

        conn.commit()


def get_active_chats():

    with closing(get_connection()) as conn:

        rows = conn.execute("""
            SELECT chat_id, chat_type, title
            FROM chats
            WHERE active = 1
            ORDER BY rowid
        """).fetchall()

        return [
            dict(row)
            for row in rows
        ]


def deactivate_chat(chat_id):

    with closing(get_connection()) as conn:

        conn.execute("""
            UPDATE chats
            SET active = 0
            WHERE chat_id = ?
        """, (
            str(chat_id),
        ))

        conn.commit()


def chat_count():

    with closing(get_connection()) as conn:

        row = conn.execute("""
            SELECT COUNT(*)
            FROM chats
            WHERE active = 1
        """).fetchone()

        return row[0]
