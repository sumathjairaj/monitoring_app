import logging

from werkzeug.security import check_password_hash

from app import DEMO_SECRET_KEY, PASSWORD_HASH, create_app


def test_login_success(client):
    response = client.post(
        "/login",
        data={"username": "admin", "password": "admin"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Servers" in response.data
    assert b"No servers yet." in response.data
    with client.session_transaction() as sess:
        assert sess["user"] == "admin"


def test_wrong_password_stays_on_sign_in(client):
    response = client.post(
        "/login",
        data={"username": "admin", "password": "wrong"},
    )
    assert response.status_code == 200
    assert b"Invalid username or password." in response.data
    assert b"Sign in" in response.data
    assert b"wrong" not in response.data
    with client.session_transaction() as sess:
        assert "user" not in sess


def test_wrong_username_uses_the_same_error(client):
    response = client.post(
        "/login",
        data={"username": "other", "password": "admin"},
    )
    assert response.status_code == 200
    assert b"Invalid username or password." in response.data
    with client.session_transaction() as sess:
        assert "user" not in sess


def test_stored_check_value_is_not_the_plain_password():
    assert PASSWORD_HASH != "admin"
    assert "admin" not in PASSWORD_HASH
    assert check_password_hash(PASSWORD_HASH, "admin")
    assert not check_password_hash(PASSWORD_HASH, "wrong")


def test_failed_login_does_not_log_the_password(client, caplog):
    caplog.set_level(logging.DEBUG)
    response = client.post(
        "/login",
        data={"username": "admin", "password": "s3cret-value"},
    )
    assert b"s3cret-value" not in response.data
    assert "s3cret-value" not in caplog.text


def test_session_cookie_is_httponly_and_samesite(client):
    response = client.post(
        "/login",
        data={"username": "admin", "password": "admin"},
    )
    cookie = ",".join(response.headers.getlist("Set-Cookie"))
    assert "HttpOnly" in cookie
    assert "SameSite=Lax" in cookie


def test_anonymous_visit_goes_to_sign_in(client):
    response = client.get("/")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_anonymous_unknown_page_goes_to_sign_in(client):
    response = client.get("/missing")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_sign_out_clears_the_session(client, login):
    login()
    with client.session_transaction() as sess:
        assert sess["user"] == "admin"
    response = client.post("/logout")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]
    with client.session_transaction() as sess:
        assert "user" not in sess
    home = client.get("/")
    assert home.status_code == 302
    assert "/login" in home.headers["Location"]


def test_plain_password_is_not_stored_in_the_database(app, client):
    client.post("/login", data={"username": "admin", "password": "admin"})
    blob = open(app.config["DB_PATH"], "rb").read()
    assert b"admin" not in blob


def test_secret_key_comes_from_the_environment(monkeypatch, tmp_path):
    monkeypatch.setenv("SECRET_KEY", "env-secret")
    app = create_app(db_path=tmp_path / "servers.db")
    assert app.secret_key == "env-secret"


def test_secret_key_fallback_is_demo_only(monkeypatch, tmp_path):
    monkeypatch.delenv("SECRET_KEY", raising=False)
    app = create_app(db_path=tmp_path / "servers.db")
    assert app.secret_key == DEMO_SECRET_KEY
