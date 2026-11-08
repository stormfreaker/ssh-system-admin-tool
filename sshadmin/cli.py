"""Command-line entry point: subcommands, or an interactive menu with no arguments."""

from __future__ import annotations

import argparse
import logging
import sys

from . import __version__, local
from .config import ConfigError, load_config
from .remote import RemoteError, RemoteHost


def _remote_ls(args) -> int:
    with RemoteHost(load_config(args.env_file)) as host:
        for name in host.list_home():
            print(name)
    return 0


def _remote_backup(args) -> int:
    with RemoteHost(load_config(args.env_file)) as host:
        print(f"Backed up to: {host.backup_file(args.path)}")
    return 0


def _menu(args) -> int:
    actions = {
        "1": ("Show date and time", lambda: print(local.now())),
        "2": ("Show local IP address", lambda: print(local.primary_ip())),
        "3": ("List remote home directory", lambda: _remote_ls(args)),
        "4": ("Back up a remote file", lambda: _remote_backup(
            argparse.Namespace(env_file=args.env_file, path=input("Remote file path: ").strip()))),
        "5": ("Save a web page", lambda: print("Saved:", local.save_web_page(
            input("URL: ").strip(), input("Save as: ").strip()))),
    }
    while True:
        print("\nMenu:")
        for key, (label, _) in actions.items():
            print(f"  {key} - {label}")
        print("  Q - Quit")
        choice = input("Choice: ").strip().upper()
        if choice == "Q":
            return 0
        if choice not in actions:
            print("Invalid choice.")
            continue
        try:
            actions[choice][1]()
        except (ConfigError, RemoteError, ValueError, OSError) as exc:
            print(f"Error: {exc}")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="sshadmin", description="Safe helpers for administering a Linux host over SSH."
    )
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    p.add_argument("--env-file", default=".env", help="settings file (default: .env)")
    p.add_argument("-v", "--verbose", action="store_true", help="debug logging")
    sub = p.add_subparsers(dest="cmd")
    sub.add_parser("time", help="show local date and time").set_defaults(
        func=lambda a: print(local.now()) or 0)
    sub.add_parser("ip", help="show local IP address").set_defaults(
        func=lambda a: print(local.primary_ip()) or 0)
    sub.add_parser("ls", help="list the remote home directory").set_defaults(func=_remote_ls)
    b = sub.add_parser("backup", help="copy a remote file to <file>.old")
    b.add_argument("path")
    b.set_defaults(func=_remote_backup)
    w = sub.add_parser("fetch", help="save a web page to a local file")
    w.add_argument("url")
    w.add_argument("dest")
    w.set_defaults(func=lambda a: print("Saved:", local.save_web_page(a.url, a.dest)) or 0)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.WARNING,
                        format="%(levelname)s %(name)s: %(message)s")
    func = getattr(args, "func", _menu)
    try:
        return func(args)
    except (ConfigError, RemoteError, ValueError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())
