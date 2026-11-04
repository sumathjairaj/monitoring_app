"""SQLite helpers for server display names."""

import sqlite3
from pathlib import Path

NAME_MAX_LENGTH = 64


def connect(db_path):
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    return connection


def init_db(db_path):
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with connect(path) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS servers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE
            )
            """
        )


def list_servers(db_path):
    with connect(db_path) as connection:
        rows = connection.execute(
            "SELECT id, name FROM servers ORDER BY name COLLATE NOCASE, id"
        ).fetchall()
    return [{"id": row["id"], "name": row["name"]} for row in rows]


def get_server(db_path, server_id):
    with connect(db_path) as connection:
        row = connection.execute(
            "SELECT id, name FROM servers WHERE id = ?",
            (server_id,),
        ).fetchone()
    if row is None:
        return None
    return {"id": row["id"], "name": row["name"]}


def insert_server(db_path, name):
    cleaned = (name or "").strip()
    if not cleaned:
        raise ValueError("empty")
    if len(cleaned) > NAME_MAX_LENGTH:
        raise ValueError("long")
    try:
        with connect(db_path) as connection:
            cursor = connection.execute(
                "INSERT INTO servers (name) VALUES (?)",
                (cleaned,),
            )
            return cursor.lastrowid
    except sqlite3.IntegrityError as exc:
        raise ValueError("duplicate") from exc


def delete_server(db_path, server_id):
    with connect(db_path) as connection:
        connection.execute("DELETE FROM servers WHERE id = ?", (server_id,))
