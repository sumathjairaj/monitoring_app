import pytest

from app import create_app


@pytest.fixture
def app(tmp_path):
    return create_app(db_path=tmp_path / "servers.db", secret_key="test-secret")


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def login(client):
    def _login(username="admin", password="admin", follow_redirects=False):
        return client.post(
            "/login",
            data={"username": username, "password": password},
            follow_redirects=follow_redirects,
        )

    return _login
