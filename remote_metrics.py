"""Read-only metrics from a Linux server over SSH.

The host, user, and port are passed as separate SSH arguments. The remote
command is fixed and does not include those values.
"""

import re
import subprocess

from metrics import shape_metrics

REMOTE_COLLECT = r"""
t1=$(awk '/^cpu /{idle=$5+$6; total=0; for(i=2;i<=NF;i++) total+=$i; printf "%s %s", total, idle}' /proc/stat)
sleep 0.2
t2=$(awk '/^cpu /{idle=$5+$6; total=0; for(i=2;i<=NF;i++) total+=$i; printf "%s %s", total, idle}' /proc/stat)
awk -v t1="$t1" -v t2="$t2" 'BEGIN {
  split(t1, a, " "); split(t2, b, " ");
  dt=b[1]-a[1]; di=b[2]-a[2];
  pct=0;
  if (dt>0) pct=(1-di/dt)*100;
  if (pct<0) pct=0;
  if (pct>100) pct=100;
  printf "cpu_percent=%.1f\n", pct
}'
awk '
  /^MemTotal:/ {t=$2}
  /^MemAvailable:/ {avail=$2}
  /^MemFree:/ {free=$2}
  /^Buffers:/ {buffers=$2}
  /^Cached:/ {cached=$2}
  END {
    if (avail+0==0) avail=free+buffers+cached;
    used=t-avail;
    if (used<0) used=0;
    pct=0;
    if (t>0) pct=(used/t)*100;
    printf "mem_total=%d\nmem_used=%d\nmem_percent=%.1f\n", t*1024, used*1024, pct
  }
' /proc/meminfo
awk '
  NR>2 {
    iface=$1;
    sub(/:.*/, "", iface);
    rest=$0;
    sub(/^[^:]*:/, "", rest);
    n=split(rest, f, " ");
    if (n>=9) {
      printf "iface %s %s %s\n", iface, f[1], f[9];
      recv+=f[1]; sent+=f[9];
    }
  }
  END { printf "bytes_recv=%d\nbytes_sent=%d\n", recv+0, sent+0 }
' /proc/net/dev
{ ss -H -lntup 2>/dev/null || ss -H -lntu 2>/dev/null || true; } |
while IFS= read -r line; do
  printf 'ss %s\n' "$line"
done
"""

_IFACE_RE = re.compile(r"^[A-Za-z0-9_.:-]{1,32}$")
_PROCESS_RE = re.compile(r'\(\("([^"]+)"')


class RemoteError(Exception):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def ssh_argv(host, port, username):
    from storage import valid_host, valid_port, valid_username

    if not valid_host(host) or not valid_username(username) or not valid_port(port):
        raise RemoteError("host")
    return [
        "ssh",
        "-T",
        "-p",
        str(int(port)),
        "-l",
        username,
        "-o",
        "BatchMode=yes",
        "-o",
        "ConnectTimeout=5",
        "-o",
        "StrictHostKeyChecking=yes",
        host,
        REMOTE_COLLECT,
    ]


def _split_address(value):
    if value.startswith("["):
        host, separator, port = value.rpartition("]:")
        if separator and host.startswith("["):
            return host[1:], port
    host, separator, port = value.rpartition(":")
    if not separator:
        return None
    return host, port


def _parse_ss(line):
    parts = line.split()
    if len(parts) < 5:
        return None
    protocol = parts[0].lower()
    if protocol not in ("tcp", "udp"):
        return None
    if protocol == "tcp" and parts[1].upper() != "LISTEN":
        return None
    address = _split_address(parts[4])
    if address is None or not address[1].isdigit():
        return None
    process = "unknown"
    match = _PROCESS_RE.search(line)
    if match:
        process = match.group(1)[:64]
    return {
        "protocol": protocol.upper(),
        "port": int(address[1]),
        "process": process,
        "address": address[0],
    }


def parse_remote_report(text):
    values = {}
    interfaces = []
    ports = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or len(line) > 400:
            continue
        if line.startswith("ss "):
            port = _parse_ss(line[3:])
            if port is not None and len(ports) < 500:
                ports.append(port)
            continue
        if line.startswith("iface "):
            parts = line.split()
            if len(parts) != 4 or not _IFACE_RE.match(parts[1]):
                continue
            if not parts[2].isdigit() or not parts[3].isdigit():
                continue
            if len(interfaces) < 100:
                interfaces.append(
                    {
                        "name": parts[1],
                        "bytes_recv": int(parts[2]),
                        "bytes_sent": int(parts[3]),
                    }
                )
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key] = value
    required = (
        "cpu_percent",
        "mem_total",
        "mem_used",
        "mem_percent",
        "bytes_recv",
        "bytes_sent",
    )
    if any(key not in values for key in required):
        raise RemoteError("badreport")
    ports.sort(key=lambda row: (row["protocol"], row["port"], row["address"], row["process"]))
    return {
        "cpu_percent": values["cpu_percent"],
        "memory_used": values["mem_used"],
        "memory_total": values["mem_total"],
        "memory_percent": values["mem_percent"],
        "bytes_recv": values["bytes_recv"],
        "bytes_sent": values["bytes_sent"],
        "interfaces": interfaces,
        "ports": ports,
    }


def _classify_ssh_failure(stderr):
    text = (stderr or "").lower()
    if "host key verification failed" in text or "authenticity of host" in text:
        return "hostkey"
    if "permission denied" in text:
        return "auth"
    return "unreachable"


def _run_ssh(command):
    try:
        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise RemoteError("timeout") from exc


def read_remote_metrics(host, port, username, runner=None):
    command = ssh_argv(host, port, username)
    completed = (runner or _run_ssh)(command)
    if completed.returncode != 0:
        raise RemoteError(_classify_ssh_failure(completed.stderr))
    try:
        snapshot = parse_remote_report(completed.stdout or "")
    except RemoteError:
        raise
    except (TypeError, ValueError) as exc:
        raise RemoteError("badreport") from exc
    return shape_metrics(snapshot, lambda _pid: "")
