"""SQLite helpers for server names and SSH targets."""

import ipaddress
import re
import sqlite3
from pathlib import Path

NAME_MAX_LENGTH = 64
HOST_RE = re.compile(
    r"^(?=.{1,253}$)(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)(?:\.(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?))*$"
)
USERNAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_-]{0,31}$")


def connect(db_path):
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    return connection


def valid_host(value):
    text = (value or "").strip()
    if not text or text.startswith("-"):
        return False
    if HOST_RE.match(text):
        labels = text.split(".")
        if all(label.isdigit() for label in labels):
            return _is_ip(text)
        return True
    return _is_ip(text)


def _is_ip(text):
    try:
        ipaddress.ip_address(text)
    except ValueError:
        return False
    return True


def valid_username(value):
    return bool(USERNAME_RE.match((value or "").strip()))


def valid_port(value):
    try:
        port = int(value)
    except (TypeError, ValueError):
        return False
    return 1 <= port <= 65535


def init_db(db_path):
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with connect(path) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS servers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                host TEXT,
                port INTEGER,
                username TEXT
            )
            """
        )
        columns = {row["name"] for row in connection.execute("PRAGMA table_info(servers)")}
        if "host" not in columns:
            connection.execute("ALTER TABLE servers ADD COLUMN host TEXT")
        if "port" not in columns:
            connection.execute("ALTER TABLE servers ADD COLUMN port INTEGER")
        if "username" not in columns:
            connection.execute("ALTER TABLE servers ADD COLUMN username TEXT")


def _server_from_row(row):
    return {
        "id": row["id"],
        "name": row["name"],
        "host": row["host"],
        "port": row["port"],
        "username": row["username"],
    }


def list_servers(db_path):
    with connect(db_path) as connection:
        rows = connection.execute(
            """
            SELECT id, name, host, port, username
            FROM servers
            ORDER BY name COLLATE NOCASE, id
            """
        ).fetchall()
    return [_server_from_row(row) for row in rows]


def get_server(db_path, server_id):
    with connect(db_path) as connection:
        row = connection.execute(
            """
            SELECT id, name, host, port, username
            FROM servers
            WHERE id = ?
            """,
            (server_id,),
        ).fetchone()
    if row is None:
        return None
    return _server_from_row(row)


def insert_server(db_path, name, host=None, port=None, username=None):
    cleaned = (name or "").strip()
    if not cleaned:
        raise ValueError("empty")
    if len(cleaned) > NAME_MAX_LENGTH:
        raise ValueError("long")

    remote_host = (host or "").strip()
    remote_user = (username or "").strip()
    port_text = "" if port is None else str(port).strip()
    if remote_host or remote_user or port_text not in ("", "22"):
        if not valid_host(remote_host):
            raise ValueError("host")
        if not valid_username(remote_user):
            raise ValueError("user")
        if port_text == "":
            remote_port = 22
        elif valid_port(port_text):
            remote_port = int(port_text)
        else:
            raise ValueError("port")
    else:
        remote_host = None
        remote_user = None
        remote_port = None

    try:
        with connect(db_path) as connection:
            cursor = connection.execute(
                """
                INSERT INTO servers (name, host, port, username)
                VALUES (?, ?, ?, ?)
                """,
                (cleaned, remote_host, remote_port, remote_user),
            )
            return cursor.lastrowid
    except sqlite3.IntegrityError as exc:
        raise ValueError("duplicate") from exc


def delete_server(db_path, server_id):
    with connect(db_path) as connection:
        connection.execute("DELETE FROM servers WHERE id = ?", (server_id,))
