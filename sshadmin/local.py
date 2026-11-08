"""Local-machine helpers (no SSH needed)."""

from __future__ import annotations

import socket
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import requests

MAX_PAGE_BYTES = 10 * 1024 * 1024


def now() -> str:
    return datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")


def primary_ip() -> str:
    """IP of the interface used for outbound traffic.

    ``gethostbyname(gethostname())`` often returns 127.0.1.1 on Linux, so instead we
    open a UDP socket towards a public address (no packet is sent) and read its source.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        try:
            s.connect(("192.0.2.1", 80))  # TEST-NET-1, never actually contacted
            return s.getsockname()[0]
        except OSError:
            return "127.0.0.1"


def save_web_page(url: str, dest: str | Path, timeout: float = 15.0) -> Path:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValueError("URL must start with http:// or https://")
    dest = Path(dest)
    if dest.exists():
        raise FileExistsError(f"{dest} already exists; refusing to overwrite")

    with requests.get(url, timeout=timeout, stream=True) as resp:
        resp.raise_for_status()
        chunks, size = [], 0
        for chunk in resp.iter_content(65536):
            size += len(chunk)
            if size > MAX_PAGE_BYTES:
                raise ValueError("Page is larger than 10 MB; aborting")
            chunks.append(chunk)
    dest.write_bytes(b"".join(chunks))
    return dest
