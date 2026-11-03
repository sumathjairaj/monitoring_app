# Demo Monitoring Infrastructure — Requirements

## 1. Purpose

Internal teams currently sign in to Linux servers to check live CPU, memory, network, and port usage. This demo is a small local web app that shows those figures for the machine it runs on, so L1, L2, L3, infrastructure, and application teams can look them up in a browser.

The app runs on the same computer as Cursor. It is a demo, with one shared login and no remote access to other hosts.

## 2. Users

| Team | Use |
| --- | --- |
| L1 | See whether CPU, memory, or ports look abnormal |
| L2 | Check the same live figures while investigating an issue |
| L3, infrastructure, and application development | Open a named server view and read current usage |

Everyone uses the same demo account. Separate roles and permissions are out of scope.

## 3. Demo decisions

| Topic | Decision |
| --- | --- |
| What is monitored | The Linux machine where the app is running |
| Adding a server | A display name for that same machine. Several names may exist; each one shows this host’s live metrics |
| Sign-in | Username `admin`. Password `admin`, checked against a hash created when the app starts |
| What users can change | Add a server name and remove a server name |
| Metrics pages | View only. The app does not open a shell or change the host |
| Refresh | The server view loads fresh metrics about every 15 seconds |
| Ports | Listening TCP and UDP ports, with port, process name, and address |

## 4. Technology

- Python web app using Flask
- Server-rendered pages with a clear, readable layout
- Local OS metrics (for example `psutil`, `/proc`, or `ss`)
- Password check with a standard password hash (Werkzeug or the Python standard library). The plain password is not written to disk

## 5. Features

### 5.1 Sign in

- Unauthenticated visitors see only the sign-in page.
- Username is `admin`. Password is `admin`.
- On startup the app hashes `admin` and keeps that hash for the life of the process.
- A successful sign-in starts a session. A sign-out control ends it.
- A wrong password shows an error and stays on the sign-in page.

### 5.2 Server list

- After sign-in, the home page lists server names already added.
- The user can add a server by entering a display name and saving it.
- The user can remove a server name. Removal deletes the name only. It does not change the host.
- Names are stored locally for the running demo (a small SQLite file or equivalent under the app directory).
- Empty name is rejected. A duplicate name is rejected.

### 5.3 Server view (read only)

Opening a name shows the current metrics for this machine:

- **CPU** — overall usage percent
- **Memory** — used, total, and percent
- **Network** — received and sent bytes (or current rate) for the active interfaces
- **Listening ports** — TCP and UDP rows with port, process name, and local address

The page refreshes this data about every 15 seconds. There is no terminal, no remote command, and no control to restart services or edit host configuration.

## 6. Pages

1. **Sign in** — username, password, submit.
2. **Servers** — list, add form, remove action, link to each server view.
3. **Server detail** — the four metric sections above, labeled with the chosen display name and the fact that the source is this computer.

Shared layout: short title, signed-in state, and sign out. Use a simple modern style (spacing, readable type, cards or a compact table) so the page is easy to scan.

## 7. Run locally

From the project directory, with Python 3 available:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open `http://127.0.0.1:8000` and sign in with `admin` / `admin`. Port 5000 is already in use on this machine, so the demo uses 8000.

The app binds to localhost only.

## 8. Acceptance

- Sign-in with `admin` / `admin` opens the server list. Any other password does not.
- The password is checked as a hash. The app does not store `admin` in a database or config file as plain text.
- A signed-in user can add a display name and see it in the list, then remove it.
- Opening a name shows CPU, memory, network, and listening ports from this Linux machine.
- Those figures update about every 15 seconds without signing in to a shell.
- The metrics page has no action that changes the host.
- Another machine cannot be monitored from this demo.

## 9. Out of scope

- SSH or agents on other servers
- Alerts, history charts, and log collection
- More than one user account, password change, and role-based access
- Editing a server name in place
- Deploying anywhere other than this computer
