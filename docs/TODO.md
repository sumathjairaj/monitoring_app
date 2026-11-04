# Implementation TODO

Local demo only. Do one section at a time and check the boxes when that section is done. Each section includes the code change, a security check, and a short doc update.

Run the app only on this machine at `http://127.0.0.1:8000`. Sign-in is `admin` / `admin`. The password is hashed in memory at startup and is never written to disk.

## 1. Project initialization and basic UI

- [x] Add `app.py`, `requirements.txt` (`flask`), and `templates/` with a base layout.
- [x] Add a home page that renders: title, one-line description, and an empty “Servers” area.
- [x] Use a simple readable style (spacing, type, one card). No metrics and no forms yet.
- [x] Bind Flask to `127.0.0.1` and port `5000`. Port 5000 was in use, so the app listens on `8000`.
- [x] **Security:** Add `.gitignore` for `.venv/`, `__pycache__/`, `*.db`, and `.env`. Do not commit secrets.
- [x] **Documentation:** Add a short `README.md` with the four local run commands from `docs/requirements.md` and the localhost URL.

## 2. Sign-in and unit tests

- [x] Add a sign-in page (username, password, submit) and a sign-out control.
- [x] On startup, hash the demo password with Werkzeug. Compare with `check_password_hash`.
- [x] Correct `admin` / `admin` starts a session and shows the home page. Anything else shows an error and stays on sign-in.
- [x] Add `tests/test_auth.py`: success, wrong password, and the stored check value is not the plain password.
- [x] **Security:** Session cookie is `HttpOnly` and `SameSite=Lax`. Use one generic error. Do not log the password.
- [x] **Documentation:** In `README.md`, document the demo account and that only a hash is held in memory.

## 3. GitHub Actions

- [x] Add `.github/workflows/ci.yml` that installs dependencies and runs `pytest` on push and pull request.
- [x] **Security:** No secrets in the workflow. Actions are pinned to a major version. CI does not deploy.
- [x] **Documentation:** Add a “CI” line to `README.md`: tests run on GitHub Actions; the app itself stays local.

## 4. Require sign-in

- [x] Send unauthenticated visitors to the sign-in page. Signed-in users can open the home page.
- [x] Sign-out clears the session.
- [x] Extend tests for an anonymous visit and for sign-out.
- [x] **Security:** Set a `SECRET_KEY` from the environment for real use. A local fallback is fine for this demo and must be noted as demo-only.
- [x] **Documentation:** Note in `README.md` that pages after sign-in require a session.

## 5. Store server names

- [x] Add a local SQLite file under the app directory with one table: id and display name.
- [x] Add a small data helper: list names, insert name, delete by id.
- [x] Add unit tests with a temporary database: empty name rejected, duplicate name rejected, delete removes one row.
- [x] **Security:** Use parameterized queries only. Keep the database file out of git.
- [x] **Documentation:** Note the SQLite file path in `README.md`.

## 6. Add a server

- [x] On the home page, add a form with one text field and a save button.
- [x] Show the saved name in the list. Show a short error for an empty or duplicate name.
- [x] **Security:** Accept POST only from a signed-in session. Limit the name length (for example 64 characters). Render the name as text.
- [x] **Documentation:** Describe add-server behavior in `README.md` (display name for this computer only).

## 7. Remove a server

- [x] Add a remove button on each list row.
- [x] Removal deletes that name and reloads the list.
- [x] Add a test that remove does not affect other rows.
- [x] **Security:** Remove uses POST, and only a signed-in session can call it. Unknown ids do nothing harmful.
- [x] **Documentation:** Note in `README.md` that remove deletes the name only.

## 8. Read local metrics

- [x] Add a function that returns CPU percent, memory used/total/percent, network received/sent, and listening TCP/UDP ports (port, process, address).
- [x] Use a read-only library such as `psutil`. Add a test with a fake snapshot so CI does not depend on live host numbers.
- [x] **Security:** Do not pass user input into OS commands. Do not use a shell. Do not include a terminal or any host control.
- [x] **Documentation:** List the four metric groups in `README.md`.

## 9. Server detail page

- [x] Link each name to a detail page titled with that name.
- [x] Show the four metric groups and the line “Source: this computer”.
- [x] Unknown ids return 404.
- [x] **Security:** Detail is signed-in only. Jinja escapes the server name. The page has no action that changes the host.
- [x] **Documentation:** Describe the detail page in `README.md`.

## 10. Refresh every 15 seconds

- [x] The detail page reloads its metrics about every 15 seconds.
- [x] **Security:** Refresh calls the same signed-in page only. It does not open a new unauthenticated endpoint.
- [x] **Documentation:** State the 15-second refresh in `README.md`.

## 11. Demo check

- [x] Walk through `docs/requirements.md` section 8 on `http://127.0.0.1:8000`.
- [x] **Security:** Confirm the app listens on localhost, the database and `.env` are untracked, and no SSH or other-host settings exist.
- [x] **Documentation:** Leave `README.md` as the only run guide: four commands, URL, and `admin` / `admin`.
