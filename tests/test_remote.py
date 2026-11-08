from unittest.mock import MagicMock

import paramiko
import pytest

from sshadmin.config import SSHConfig
from sshadmin.remote import RemoteError, RemoteHost


def fake_client(responses):
    """responses: list of (exit_status, stdout, stderr), returned in order."""
    client = MagicMock(spec=paramiko.SSHClient)
    calls = []

    def exec_command(cmd, timeout=None):
        calls.append(cmd)
        status, out, err = responses.pop(0)
        stdout, stderr = MagicMock(), MagicMock()
        stdout.channel.recv_exit_status.return_value = status
        stdout.read.return_value = out.encode()
        stderr.read.return_value = err.encode()
        return MagicMock(), stdout, stderr

    client.exec_command.side_effect = exec_command
    return client, calls


CFG = SSHConfig(host="h", username="u")


def test_rejects_unknown_host_keys():
    client, _ = fake_client([])
    with RemoteHost(CFG, client):
        pass
    policy = client.set_missing_host_key_policy.call_args.args[0]
    assert isinstance(policy, paramiko.RejectPolicy)


def test_backup_quotes_malicious_path():
    client, calls = fake_client([(0, "", ""), (0, "", "")])
    evil = "/srv/x; rm -rf ~"
    with RemoteHost(CFG, client) as host:
        assert host.backup_file(evil) == evil + ".old"
    assert calls[1] == "cp -p -- '/srv/x; rm -rf ~' '/srv/x; rm -rf ~.old'"


def test_backup_reports_failure():
    client, _ = fake_client([(0, "", ""), (1, "", "Permission denied")])
    with RemoteHost(CFG, client) as host, pytest.raises(RemoteError, match="Permission denied"):
        host.backup_file("/etc/shadow")


def test_backup_missing_file():
    client, _ = fake_client([(1, "", "")])
    with RemoteHost(CFG, client) as host, pytest.raises(RemoteError, match="Not a regular file"):
        host.backup_file("/nope")


def test_list_home():
    client, _ = fake_client([(0, ".bashrc\nnotes.txt\n", "")])
    with RemoteHost(CFG, client) as host:
        assert host.list_home() == [".bashrc", "notes.txt"]


def test_connection_error_wrapped():
    client, _ = fake_client([])
    client.connect.side_effect = paramiko.SSHException("Server 'h' not found in known_hosts")
    with pytest.raises(RemoteError, match="known_hosts"):
        with RemoteHost(CFG, client):
            pass
