import os
from functools import wraps
from pathlib import Path

from flask import Flask, abort, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from metrics import read_local_metrics
from storage import delete_server, get_server, init_db, insert_server, list_servers

DEMO_USERNAME = "admin"
# Hashed when the process starts. Only this hash is kept for sign-in checks.
PASSWORD_HASH = generate_password_hash("admin")

# Demo-only fallback when SECRET_KEY is unset. Set SECRET_KEY for any real use.
DEMO_SECRET_KEY = "demo-only-local-fallback"

LOGIN_ERROR = "Invalid username or password."
ADD_ERRORS = {
    "empty": "Enter a server name.",
    "duplicate": "That name is already in the list.",
    "long": "Name must be 64 characters or fewer.",
}

DEFAULT_DB_PATH = Path(__file__).resolve().parent / "servers.db"


def create_app(db_path=None, secret_key=None, metrics_reader=None):
    app = Flask(__name__)
    app.config["SECRET_KEY"] = secret_key or os.environ.get("SECRET_KEY") or DEMO_SECRET_KEY
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["DB_PATH"] = str(db_path or DEFAULT_DB_PATH)
    app.config["METRICS_READER"] = metrics_reader or read_local_metrics

    init_db(app.config["DB_PATH"])

    def login_required(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if session.get("user") != DEMO_USERNAME:
                return redirect(url_for("login"))
            return view(*args, **kwargs)

        return wrapped

    @app.context_processor
    def inject_signed_in():
        return {"signed_in": session.get("user") == DEMO_USERNAME}

    @app.get("/login")
    @app.post("/login")
    def login():
        if session.get("user") == DEMO_USERNAME:
            return redirect(url_for("home"))
        error = None
        if request.method == "POST":
            username = request.form.get("username", "")
            password = request.form.get("password", "")
            if username == DEMO_USERNAME and check_password_hash(PASSWORD_HASH, password):
                session.clear()
                session["user"] = DEMO_USERNAME
                return redirect(url_for("home"))
            error = LOGIN_ERROR
        return render_template("login.html", error=error)

    @app.post("/logout")
    def logout():
        session.clear()
        return redirect(url_for("login"))

    @app.get("/")
    @login_required
    def home():
        error = ADD_ERRORS.get(request.args.get("error", ""))
        servers = list_servers(app.config["DB_PATH"])
        return render_template("index.html", servers=servers, error=error)

    @app.post("/servers")
    @login_required
    def add_server():
        try:
            insert_server(app.config["DB_PATH"], request.form.get("name", ""))
        except ValueError as exc:
            return redirect(url_for("home", error=str(exc)))
        return redirect(url_for("home"))

    @app.post("/servers/<int:server_id>/delete")
    @login_required
    def remove_server(server_id):
        delete_server(app.config["DB_PATH"], server_id)
        return redirect(url_for("home"))

    @app.get("/servers/<int:server_id>")
    @login_required
    def server_detail(server_id):
        server = get_server(app.config["DB_PATH"], server_id)
        if server is None:
            abort(404)
        metrics = app.config["METRICS_READER"]()
        return render_template("detail.html", server=server, metrics=metrics)

    @app.errorhandler(404)
    def not_found(_error):
        if session.get("user") != DEMO_USERNAME:
            return redirect(url_for("login"))
        return render_template("not_found.html"), 404

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000)
