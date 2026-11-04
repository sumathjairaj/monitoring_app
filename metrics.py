"""Read-only metrics for this computer. No shell and no user input."""

import socket

import psutil


def format_bytes(num):
    size = float(num)
    units = ("B", "KB", "MB", "GB", "TB")
    for unit in units:
        if size < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{int(size)} B"
            return f"{size:.1f} {unit}"
        size /= 1024


def process_name(pid):
    if not pid:
        return ""
    try:
        return psutil.Process(pid).name()
    except (psutil.Error, OSError):
        return ""


def listening_ports(connections, resolve_process):
    rows = []
    for conn in connections:
        local = getattr(conn, "laddr", None)
        if not local:
            continue
        sock_type = getattr(conn, "type", None)
        status = getattr(conn, "status", None)
        if sock_type == socket.SOCK_STREAM:
            if status != "LISTEN":
                continue
            protocol = "TCP"
        elif sock_type == socket.SOCK_DGRAM:
            protocol = "UDP"
        else:
            continue
        pid = getattr(conn, "pid", None)
        name = getattr(conn, "process_name", "") or ""
        if not name and pid:
            try:
                name = resolve_process(pid) or ""
            except (psutil.Error, OSError):
                name = ""
        rows.append(
            {
                "protocol": protocol,
                "port": local.port,
                "process": name or "unknown",
                "address": local.ip,
            }
        )
    rows.sort(key=lambda row: (row["protocol"], row["port"], row["address"], row["process"]))
    return rows


def shape_metrics(snapshot, resolve_process):
    """Build the page model from a snapshot so tests never read the host."""
    interfaces = []
    for item in snapshot.get("interfaces", []):
        interfaces.append(
            {
                "name": item["name"],
                "bytes_recv": format_bytes(item["bytes_recv"]),
                "bytes_sent": format_bytes(item["bytes_sent"]),
            }
        )
    interfaces.sort(key=lambda item: item["name"])
    if "ports" in snapshot:
        ports = list(snapshot["ports"])
    else:
        ports = listening_ports(snapshot.get("connections", []), resolve_process)
    return {
        "cpu_percent": round(float(snapshot["cpu_percent"]), 1),
        "memory_used": format_bytes(snapshot["memory_used"]),
        "memory_total": format_bytes(snapshot["memory_total"]),
        "memory_percent": round(float(snapshot["memory_percent"]), 1),
        "bytes_recv": format_bytes(snapshot["bytes_recv"]),
        "bytes_sent": format_bytes(snapshot["bytes_sent"]),
        "interfaces": interfaces,
        "ports": ports,
    }


class _NamedConnection:
    def __init__(self, conn, process_name):
        self.type = conn.type
        self.status = conn.status
        self.laddr = conn.laddr
        self.pid = getattr(conn, "pid", None)
        self.process_name = process_name


def _owned_listeners():
    """Map listening sockets we are allowed to read to a process name."""
    owners = {}
    for proc in psutil.process_iter(["name"]):
        try:
            owned = proc.net_connections(kind="inet")
        except (psutil.AccessDenied, psutil.NoSuchProcess, psutil.ZombieProcess):
            continue
        name = proc.info.get("name") or ""
        for conn in owned:
            local = getattr(conn, "laddr", None)
            if local and name:
                owners[(conn.type, local.ip, local.port)] = name
    return owners


def _with_process_names(connections):
    owners = _owned_listeners()
    named = []
    for conn in connections:
        local = getattr(conn, "laddr", None)
        key = (conn.type, local.ip, local.port) if local else None
        named.append(_NamedConnection(conn, owners.get(key, "")))
    return named


def _active_interfaces():
    pernic = psutil.net_io_counters(pernic=True) or {}
    stats = psutil.net_if_stats()
    rows = []
    for name, counters in pernic.items():
        info = stats.get(name)
        if info is not None and not info.isup:
            continue
        rows.append(
            {
                "name": name,
                "bytes_recv": counters.bytes_recv,
                "bytes_sent": counters.bytes_sent,
            }
        )
    return rows


def read_local_metrics():
    memory = psutil.virtual_memory()
    net = psutil.net_io_counters()
    try:
        connections = _with_process_names(psutil.net_connections(kind="inet"))
    except psutil.AccessDenied:
        connections = []
    snapshot = {
        "cpu_percent": psutil.cpu_percent(interval=0.1),
        "memory_used": memory.used,
        "memory_total": memory.total,
        "memory_percent": memory.percent,
        "bytes_recv": 0 if net is None else net.bytes_recv,
        "bytes_sent": 0 if net is None else net.bytes_sent,
        "interfaces": _active_interfaces(),
        "connections": connections,
    }
    return shape_metrics(snapshot, process_name)
