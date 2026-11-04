import socket
from types import SimpleNamespace

import metrics


def _conn(sock_type, status, ip, port, pid):
    return SimpleNamespace(
        type=sock_type,
        status=status,
        laddr=SimpleNamespace(ip=ip, port=port),
        pid=pid,
    )


def test_fake_snapshot_does_not_read_the_host(monkeypatch):
    def forbid(*_args, **_kwargs):
        raise AssertionError("host metrics were read")

    monkeypatch.setattr(metrics.psutil, "cpu_percent", forbid)
    monkeypatch.setattr(metrics.psutil, "virtual_memory", forbid)
    monkeypatch.setattr(metrics.psutil, "net_io_counters", forbid)
    monkeypatch.setattr(metrics.psutil, "net_connections", forbid)
    monkeypatch.setattr(metrics.psutil, "net_if_stats", forbid)
    monkeypatch.setattr(metrics.psutil, "Process", forbid)

    snapshot = {
        "cpu_percent": 12.34,
        "memory_used": 1536,
        "memory_total": 4096,
        "memory_percent": 37.5,
        "bytes_recv": 500,
        "bytes_sent": 2048,
        "interfaces": [{"name": "lo", "bytes_recv": 500, "bytes_sent": 2048}],
        "connections": [
            _conn(socket.SOCK_STREAM, "LISTEN", "127.0.0.1", 8000, 10),
            _conn(socket.SOCK_STREAM, "ESTABLISHED", "10.0.0.5", 9999, 10),
            _conn(socket.SOCK_DGRAM, "NONE", "0.0.0.0", 53, 11),
            _conn(socket.SOCK_DGRAM, "NONE", "0.0.0.0", 68, None),
        ],
    }

    def resolve(pid):
        return {10: "python", 11: "dnsmasq"}[pid]

    result = metrics.shape_metrics(snapshot, resolve)
    assert result["cpu_percent"] == 12.3
    assert result["memory_used"] == "1.5 KB"
    assert result["memory_total"] == "4.0 KB"
    assert result["memory_percent"] == 37.5
    assert result["bytes_recv"] == "500 B"
    assert result["bytes_sent"] == "2.0 KB"
    assert result["interfaces"] == [
        {"name": "lo", "bytes_recv": "500 B", "bytes_sent": "2.0 KB"}
    ]
    assert result["ports"] == [
        {"protocol": "TCP", "port": 8000, "process": "python", "address": "127.0.0.1"},
        {"protocol": "UDP", "port": 53, "process": "dnsmasq", "address": "0.0.0.0"},
        {"protocol": "UDP", "port": 68, "process": "unknown", "address": "0.0.0.0"},
    ]
    assert all(row["port"] != 9999 for row in result["ports"])


def test_process_name_on_the_snapshot_is_kept_without_a_pid():
    conn = SimpleNamespace(
        type=socket.SOCK_STREAM,
        status="LISTEN",
        laddr=SimpleNamespace(ip="127.0.0.1", port=9),
        pid=None,
        process_name="python",
    )
    rows = metrics.listening_ports([conn], lambda _pid: "unused")
    assert rows == [
        {"protocol": "TCP", "port": 9, "process": "python", "address": "127.0.0.1"}
    ]


def test_shape_metrics_has_no_shell_dependency():
    source = open(metrics.__file__, encoding="utf-8").read()
    assert "subprocess" not in source
    assert "os.system" not in source
    assert "shell=True" not in source
