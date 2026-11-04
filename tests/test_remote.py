from types import SimpleNamespace

import pytest

from metrics import shape_metrics
from remote_metrics import REMOTE_COLLECT, RemoteError, parse_remote_report, read_remote_metrics, ssh_argv


REPORT = """
cpu_percent=12.5
mem_total=4096
mem_used=1536
mem_percent=37.5
bytes_recv=500
bytes_sent=2048
iface eth0 500 2048
iface bad name 1 2
ss tcp LISTEN 0 128 0.0.0.0:22 0.0.0.0:* users:(("sshd",pid=1,fd=3))
ss tcp ESTAB 0 0 10.0.0.5:4000 1.2.3.4:80
ss udp UNCONN 0 0 0.0.0.0:68 0.0.0.0:*
ss tcp LISTEN 0 128 [::]:443 [::]:*
"""


def test_ssh_argv_keeps_the_target_out_of_the_script():
    argv = ssh_argv("db.example", 2222, "monitor")
    assert argv[:4] == ["ssh", "-T", "-p", "2222"]
    assert argv[argv.index("-l") + 1] == "monitor"
    assert argv[-2] == "db.example"
    assert argv[-1] == REMOTE_COLLECT
    assert "db.example" not in REMOTE_COLLECT
    assert "monitor" not in REMOTE_COLLECT
    assert "2222" not in REMOTE_COLLECT


def test_ssh_argv_rejects_option_injection():
    with pytest.raises(RemoteError):
        ssh_argv("-oProxyCommand=calc", 22, "monitor")
    with pytest.raises(RemoteError):
        ssh_argv("db.example", 22, "root;id")


def test_remote_report_builds_metrics_without_a_connection():
    snapshot = parse_remote_report(REPORT)
    metrics = shape_metrics(snapshot, lambda _pid: "unused")
    assert metrics["cpu_percent"] == 12.5
    assert metrics["memory_used"] == "1.5 KB"
    assert metrics["bytes_sent"] == "2.0 KB"
    assert metrics["interfaces"] == [
        {"name": "eth0", "bytes_recv": "500 B", "bytes_sent": "2.0 KB"}
    ]
    assert metrics["ports"] == [
        {"protocol": "TCP", "port": 22, "process": "sshd", "address": "0.0.0.0"},
        {"protocol": "TCP", "port": 443, "process": "unknown", "address": "::"},
        {"protocol": "UDP", "port": 68, "process": "unknown", "address": "0.0.0.0"},
    ]


def test_read_remote_metrics_uses_the_supplied_runner():
    def runner(command):
        assert command[0] == "ssh"
        assert "203.0.113.10" in command
        return SimpleNamespace(returncode=0, stdout=REPORT, stderr="")

    metrics = read_remote_metrics("203.0.113.10", 22, "monitor", runner=runner)
    assert metrics["cpu_percent"] == 12.5
    assert metrics["ports"][0]["process"] == "sshd"


def test_authentication_failure_is_classified():
    def runner(_command):
        return SimpleNamespace(returncode=255, stdout="", stderr="Permission denied (publickey).")

    with pytest.raises(RemoteError) as caught:
        read_remote_metrics("203.0.113.10", 22, "monitor", runner=runner)
    assert str(caught.value) == "auth"


def test_remote_collector_does_not_use_a_shell():
    source = open("remote_metrics.py", encoding="utf-8").read()
    assert "shell=True" not in source
    assert "os.system" not in source
