# Demo Monitoring

Local demo of CPU, memory, network, and listening ports for this computer. Each server name is a display name for this same machine.

## Run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:8000 and sign in with `admin` / `admin`.

The app listens on localhost only. Port 5000 was already in use on this machine, so the demo uses 8000.

## Sign-in

The demo account is username `admin` and password `admin`. When the app starts it hashes that password with Werkzeug and keeps only the hash in memory. The plain password is not written to disk.

Pages after sign-in require a session. Sign out clears the session.

Set `SECRET_KEY` in the environment for any real use. If it is unset, the local demo uses a built-in fallback key. That fallback is demo-only.

## Servers

Display names are stored in `servers.db` in the application directory. On the home page, enter a name and save it to add a label for this computer. An empty name, a name longer than 64 characters, or a duplicate name is rejected. Remove deletes that name only. It does not change the host.

## Server detail

Open a name to see live figures for this computer:

- CPU — overall usage percent
- Memory — used, total, and percent
- Network — received and sent bytes
- Listening ports — TCP and UDP, with port, process, and address

The page is titled with the display name and includes the line “Source: this computer”. It reloads these metrics about every 15 seconds. The page has no control that changes the host.

## CI

Tests run on GitHub Actions. The app itself stays local.
