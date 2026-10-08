import sqlite3
from datetime import datetime

DATABASE = "chat_history.db"


def get_connection():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


def init_database():
    connection = get_connection()

    connection.execute("""
        CREATE TABLE IF NOT EXISTS chats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (chat_id) REFERENCES chats(id)
        )
    """)

    connection.commit()
    connection.close()


def create_chat(title="New Chat"):
    now = datetime.now().isoformat(timespec="seconds")

    connection = get_connection()

    cursor = connection.execute(
        """
        INSERT INTO chats (title, created_at, updated_at)
        VALUES (?, ?, ?)
        """,
        (title, now, now)
    )

    chat_id = cursor.lastrowid

    connection.commit()
    connection.close()

    return chat_id


def add_message(chat_id, role, content):
    now = datetime.now().isoformat(timespec="seconds")

    connection = get_connection()

    connection.execute(
        """
        INSERT INTO messages (chat_id, role, content, created_at)
        VALUES (?, ?, ?, ?)
        """,
        (chat_id, role, content, now)
    )

    connection.execute(
        """
        UPDATE chats
        SET updated_at = ?
        WHERE id = ?
        """,
        (now, chat_id)
    )

    connection.commit()
    connection.close()


def get_chats():
    connection = get_connection()

    chats = connection.execute(
        """
        SELECT *
        FROM chats
        ORDER BY updated_at DESC
        """
    ).fetchall()

    connection.close()

    return chats


def get_messages(chat_id):
    connection = get_connection()

    messages = connection.execute(
        """
        SELECT *
        FROM messages
        WHERE chat_id = ?
        ORDER BY id ASC
        """,
        (chat_id,)
    ).fetchall()

    connection.close()

    return messages


def get_chat(chat_id):
    connection = get_connection()

    chat = connection.execute(
        """
        SELECT *
        FROM chats
        WHERE id = ?
        """,
        (chat_id,)
    ).fetchone()

    connection.close()

    return chat


def delete_chat(chat_id):
    connection = get_connection()

    connection.execute(
        "DELETE FROM messages WHERE chat_id = ?",
        (chat_id,)
    )

    connection.execute(
        "DELETE FROM chats WHERE id = ?",
        (chat_id,)
    )

    connection.commit()
    connection.close()


init_database()