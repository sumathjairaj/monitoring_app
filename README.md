# Demo Monitoring

Local demo that will show CPU, memory, network, and listening ports for this computer. This step is the home page only.

## Run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:8000

Port 5000 was already in use on this machine, so the demo uses 8000.

The app listens on localhost only.
