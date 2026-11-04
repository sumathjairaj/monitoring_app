from storage import delete_server, get_server, init_db, insert_server, list_servers


def test_empty_name_is_rejected(tmp_path):
    db = tmp_path / "servers.db"
    init_db(db)
    try:
        insert_server(db, "   ")
    except ValueError as exc:
        assert str(exc) == "empty"
    else:
        raise AssertionError("empty name was stored")
    assert list_servers(db) == []


def test_duplicate_name_is_rejected(tmp_path):
    db = tmp_path / "servers.db"
    init_db(db)
    insert_server(db, "web")
    try:
        insert_server(db, " web ")
    except ValueError as exc:
        assert str(exc) == "duplicate"
    else:
        raise AssertionError("duplicate name was stored")
    assert [row["name"] for row in list_servers(db)] == ["web"]


def test_long_name_is_rejected(tmp_path):
    db = tmp_path / "servers.db"
    init_db(db)
    insert_server(db, "a" * 64)
    try:
        insert_server(db, "b" * 65)
    except ValueError as exc:
        assert str(exc) == "long"
    else:
        raise AssertionError("long name was stored")
    assert [row["name"] for row in list_servers(db)] == ["a" * 64]


def test_delete_removes_one_row(tmp_path):
    db = tmp_path / "servers.db"
    init_db(db)
    server_id = insert_server(db, "web")
    delete_server(db, server_id)
    assert list_servers(db) == []
    assert get_server(db, server_id) is None


def test_delete_does_not_affect_other_rows(tmp_path):
    db = tmp_path / "servers.db"
    init_db(db)
    first = insert_server(db, "alpha")
    second = insert_server(db, "beta")
    delete_server(db, first)
    remaining = list_servers(db)
    assert [row["name"] for row in remaining] == ["beta"]
    assert remaining[0]["id"] == second
    assert get_server(db, first) is None


def test_unknown_delete_leaves_rows_in_place(tmp_path):
    db = tmp_path / "servers.db"
    init_db(db)
    insert_server(db, "beta")
    delete_server(db, 9999)
    assert [row["name"] for row in list_servers(db)] == ["beta"]


def test_name_is_bound_as_data(tmp_path):
    db = tmp_path / "servers.db"
    init_db(db)
    payload = "Robert'); DROP TABLE servers;--"
    insert_server(db, payload)
    assert [row["name"] for row in list_servers(db)] == [payload]
    insert_server(db, "still-here")
    assert [row["name"] for row in list_servers(db)] == [payload, "still-here"]


def test_add_requires_a_signed_in_session(client, app):
    response = client.post("/servers", data={"name": "web"})
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]
    assert list_servers(app.config["DB_PATH"]) == []


def test_add_shows_the_name(client, login):
    login()
    response = client.post("/servers", data={"name": "web"}, follow_redirects=True)
    assert response.status_code == 200
    assert b"web" in response.data
    assert b"No servers yet." not in response.data


def test_empty_and_duplicate_names_show_errors(client, login):
    login()
    empty = client.post("/servers", data={"name": "  "}, follow_redirects=True)
    assert b"Enter a server name." in empty.data
    client.post("/servers", data={"name": "web"})
    duplicate = client.post("/servers", data={"name": "web"}, follow_redirects=True)
    assert b"That name is already in the list." in duplicate.data
    assert duplicate.data.count(b">web<") == 1


def test_unknown_error_query_is_not_rendered(client, login):
    login()
    response = client.get("/?error=%3Cscript%3E")
    assert b"<script>" not in response.data
    assert b"Enter a server name." not in response.data


def test_server_name_is_rendered_as_text(client, login):
    login()
    client.post("/servers", data={"name": "<script>alert(1)</script>"})
    response = client.get("/")
    assert b"<script>alert(1)</script>" not in response.data
    assert b"&lt;script&gt;alert(1)&lt;/script&gt;" in response.data


def test_remove_uses_post_and_leaves_other_names(client, login, app):
    login()
    client.post("/servers", data={"name": "alpha"})
    client.post("/servers", data={"name": "beta"})
    rejected = client.get("/servers/1/delete")
    assert rejected.status_code == 405
    alpha = next(row for row in list_servers(app.config["DB_PATH"]) if row["name"] == "alpha")
    response = client.post(f"/servers/{alpha['id']}/delete", follow_redirects=True)
    assert b"alpha" not in response.data
    assert b"beta" in response.data


def test_remove_of_unknown_id_keeps_the_list(client, login):
    login()
    client.post("/servers", data={"name": "beta"})
    response = client.post("/servers/9999/delete", follow_redirects=True)
    assert response.status_code == 200
    assert b"beta" in response.data


def test_anonymous_cannot_remove(client, app):
    insert_server(app.config["DB_PATH"], "beta")
    response = client.post("/servers/1/delete")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]
    assert [row["name"] for row in list_servers(app.config["DB_PATH"])] == ["beta"]


def test_detail_page_and_unknown_id(tmp_path):
    from app import create_app

    def fake_metrics():
        return {
            "cpu_percent": 12.5,
            "memory_used": "1.5 KB",
            "memory_total": "4.0 KB",
            "memory_percent": 37.5,
            "bytes_recv": "500 B",
            "bytes_sent": "2.0 KB",
            "interfaces": [{"name": "lo", "bytes_recv": "500 B", "bytes_sent": "2.0 KB"}],
            "ports": [
                {
                    "protocol": "TCP",
                    "port": 8000,
                    "process": "python",
                    "address": "127.0.0.1",
                }
            ],
        }

    app = create_app(
        db_path=tmp_path / "servers.db",
        secret_key="test-secret",
        metrics_reader=fake_metrics,
    )
    client = app.test_client()
    client.post("/login", data={"username": "admin", "password": "admin"})
    missing = client.get("/servers/42")
    assert missing.status_code == 404
    client.post("/servers", data={"name": "edge"})
    server_id = list_servers(app.config["DB_PATH"])[0]["id"]
    page = client.get(f"/servers/{server_id}")
    assert page.status_code == 200
    assert b"edge" in page.data
    assert b"Source: this computer" in page.data
    assert b"CPU" in page.data
    assert b"12.5%" in page.data
    assert b"Memory" in page.data
    assert b"1.5 KB" in page.data
    assert b"Network" in page.data
    assert b"Listening ports" in page.data
    assert b"127.0.0.1" in page.data
    assert b'<meta http-equiv="refresh" content="15">' in page.data
    assert page.data.lower().count(b"<form") == 1


def test_remote_server_is_saved_and_shown(client, login, app):
    login()
    response = client.post(
        "/servers",
        data={"name": "db", "host": "db.example", "ssh_user": "monitor", "port": "2222"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"monitor@db.example:2222" in response.data
    saved = next(row for row in list_servers(app.config["DB_PATH"]) if row["name"] == "db")
    assert saved["host"] == "db.example"
    assert saved["port"] == 2222
    assert saved["username"] == "monitor"


def test_invalid_remote_target_is_rejected(client, login, app):
    login()
    response = client.post(
        "/servers",
        data={"name": "db", "host": "bad host", "ssh_user": "monitor"},
        follow_redirects=True,
    )
    assert b"Enter a hostname or IP address." in response.data
    assert list_servers(app.config["DB_PATH"]) == []
    missing_user = client.post(
        "/servers",
        data={"name": "db", "host": "db.example", "ssh_user": ""},
        follow_redirects=True,
    )
    assert b"Enter the SSH username for that server." in missing_user.data
    bad_port = client.post(
        "/servers",
        data={"name": "db", "host": "db.example", "ssh_user": "monitor", "port": "70000"},
        follow_redirects=True,
    )
    assert b"Enter a port from 1 to 65535." in bad_port.data
    assert list_servers(app.config["DB_PATH"]) == []


def test_remote_detail_reads_the_saved_server(tmp_path):
    from app import create_app

    seen = {}

    def remote_reader(host, port, username):
        seen["target"] = (host, port, username)
        return {
            "cpu_percent": 4.0,
            "memory_used": "1.0 KB",
            "memory_total": "2.0 KB",
            "memory_percent": 50.0,
            "bytes_recv": "3.0 KB",
            "bytes_sent": "4.0 KB",
            "interfaces": [],
            "ports": [],
        }

    def local_reader():
        raise AssertionError("local metrics were read for a remote server")

    app = create_app(
        db_path=tmp_path / "servers.db",
        secret_key="test-secret",
        metrics_reader=local_reader,
        remote_reader=remote_reader,
    )
    client = app.test_client()
    client.post("/login", data={"username": "admin", "password": "admin"})
    client.post(
        "/servers",
        data={"name": "db", "host": "db.example", "ssh_user": "monitor", "port": "2222"},
    )
    server_id = list_servers(app.config["DB_PATH"])[0]["id"]
    page = client.get(f"/servers/{server_id}")
    assert page.status_code == 200
    assert b"Source: monitor@db.example:2222" in page.data
    assert b"4.0%" in page.data
    assert seen["target"] == ("db.example", 2222, "monitor")


def test_existing_database_gains_remote_columns(tmp_path):
    import sqlite3

    db = tmp_path / "servers.db"
    connection = sqlite3.connect(db)
    connection.execute(
        "CREATE TABLE servers (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE)"
    )
    connection.execute("INSERT INTO servers (name) VALUES ('local')")
    connection.commit()
    connection.close()
    init_db(db)
    rows = list_servers(db)
    assert rows == [
        {"id": 1, "name": "local", "host": None, "port": None, "username": None}
    ]


def test_detail_requires_sign_in(client, app):
    server_id = insert_server(app.config["DB_PATH"], "edge")
    response = client.get(f"/servers/{server_id}")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]
