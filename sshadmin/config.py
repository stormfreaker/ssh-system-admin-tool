"""Load connection settings from environment variables (never from source code)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


class ConfigError(ValueError):
    """Raised when required settings are missing or invalid."""


@dataclass(frozen=True)
class SSHConfig:
    host: str
    username: str
    port: int = 22
    key_file: Path | None = None
    password: str | None = None
    known_hosts: Path | None = None
    timeout: float = 10.0

    def __repr__(self) -> str:  # keep secrets out of logs and tracebacks
        pw = "***" if self.password else None
        return (
            f"SSHConfig(host={self.host!r}, username={self.username!r}, port={self.port}, "
            f"key_file={self.key_file!r}, password={pw!r}, known_hosts={self.known_hosts!r})"
        )


def _load_dotenv(path: Path) -> None:
    """Minimal .env loader so the tool has no extra dependency. Real env vars win."""
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def load_config(env_file: str | os.PathLike[str] | None = ".env") -> SSHConfig:
    if env_file:
        _load_dotenv(Path(env_file))

    host = os.environ.get("SSHADMIN_HOST", "").strip()
    username = os.environ.get("SSHADMIN_USER", "").strip()
    missing = [n for n, v in (("SSHADMIN_HOST", host), ("SSHADMIN_USER", username)) if not v]
    if missing:
        raise ConfigError(f"Missing required setting(s): {', '.join(missing)}. See .env.example.")

    try:
        port = int(os.environ.get("SSHADMIN_PORT", "22"))
    except ValueError as exc:
        raise ConfigError("SSHADMIN_PORT must be an integer") from exc
    if not 1 <= port <= 65535:
        raise ConfigError("SSHADMIN_PORT must be between 1 and 65535")

    key = os.environ.get("SSHADMIN_KEY_FILE")
    known = os.environ.get("SSHADMIN_KNOWN_HOSTS")
    password = os.environ.get("SSHADMIN_PASSWORD") or None

    return SSHConfig(
        host=host,
        username=username,
        port=port,
        key_file=Path(key).expanduser() if key else None,
        password=password,
        known_hosts=Path(known).expanduser() if known else None,
    )
