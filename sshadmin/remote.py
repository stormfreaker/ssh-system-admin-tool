"""SSH operations against the remote host, with host-key checking and safe quoting."""

from __future__ import annotations

import logging
import shlex
from dataclasses import dataclass

import paramiko

from .config import SSHConfig

log = logging.getLogger(__name__)


class RemoteError(RuntimeError):
    """A remote command failed or the connection could not be made."""


@dataclass
class CommandResult:
    exit_status: int
    stdout: str
    stderr: str

    @property
    def ok(self) -> bool:
        return self.exit_status == 0


class RemoteHost:
    """Context manager wrapping one paramiko connection.

    Unknown host keys are rejected (no silent trust-on-first-use), so add the host
    with ``ssh-keyscan`` or a first manual ``ssh`` login before using the tool.
    """

    def __init__(self, config: SSHConfig, client: paramiko.SSHClient | None = None):
        self.config = config
        self._client = client or paramiko.SSHClient()

    def __enter__(self) -> RemoteHost:
        c = self.config
        self._client.load_system_host_keys()
        if c.known_hosts:
            self._client.load_host_keys(str(c.known_hosts))
        self._client.set_missing_host_key_policy(paramiko.RejectPolicy())
        try:
            self._client.connect(
                c.host,
                port=c.port,
                username=c.username,
                key_filename=str(c.key_file) if c.key_file else None,
                password=c.password,
                timeout=c.timeout,
                allow_agent=True,
                look_for_keys=c.key_file is None and c.password is None,
            )
        except paramiko.SSHException as exc:
            raise RemoteError(f"SSH connection to {c.host}:{c.port} failed: {exc}") from exc
        except OSError as exc:
            raise RemoteError(f"Cannot reach {c.host}:{c.port}: {exc}") from exc
        log.info("Connected to %s@%s:%s", c.username, c.host, c.port)
        return self

    def __exit__(self, *exc) -> None:
        self._client.close()

    def run(self, argv: list[str]) -> CommandResult:
        """Run a command given as an argument list. Every argument is shell-quoted."""
        command = shlex.join(argv)
        log.debug("Running: %s", command)
        _, stdout, stderr = self._client.exec_command(command, timeout=self.config.timeout)
        status = stdout.channel.recv_exit_status()  # wait for the command to finish
        return CommandResult(
            status,
            stdout.read().decode(errors="replace"),
            stderr.read().decode(errors="replace"),
        )

    def list_home(self) -> list[str]:
        res = self.run(["ls", "-A", "--", "."])
        if not res.ok:
            raise RemoteError(f"ls failed: {res.stderr.strip()}")
        return [line for line in res.stdout.splitlines() if line]

    def backup_file(self, path: str, suffix: str = ".old") -> str:
        """Copy ``path`` to ``path + suffix`` (original left in place). Returns the backup path."""
        if not path or "\x00" in path:
            raise ValueError("A non-empty file path is required")
        backup = path + suffix
        check = self.run(["test", "-f", path])
        if not check.ok:
            raise RemoteError(f"Not a regular file on remote host: {path}")
        res = self.run(["cp", "-p", "--", path, backup])
        if not res.ok:
            raise RemoteError(f"Backup failed: {res.stderr.strip()}")
        log.info("Backed up %s -> %s", path, backup)
        return backup
