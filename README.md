# ssh-sysadmin-toolkit

![CI](https://github.com/stormfreaker/ssh-system-admin-tool/actions/workflows/ci.yml/badge.svg)

A small Python CLI for everyday admin tasks on a Linux host over SSH: list the remote
home directory, back up a remote file, check local time and IP, and save a web page.

It began as a university scripting assignment and was rebuilt with security in mind.
[REPORT.md](REPORT.md) is the security review of the original script and explains
each change.

## Features

| Command | What it does |
|---|---|
| `sshadmin time` | Local date and time, with timezone |
| `sshadmin ip` | IP of the local outbound interface |
| `sshadmin ls` | List the remote home directory |
| `sshadmin backup <path>` | Copy a remote file to `<path>.old` (keeps the original) |
| `sshadmin fetch <url> <file>` | Save a web page (http/https, 10 MB cap, never overwrites) |
| `sshadmin` | Interactive menu with the same actions |

## Security design

- **No secrets in code.** Settings come from environment variables or a git-ignored `.env`.
- **Key-based auth first.** SSH keys and the SSH agent work out of the box; a password is an opt-in fallback.
- **Host keys are verified.** Unknown hosts are rejected (`RejectPolicy`), so a man-in-the-middle can't pass silently.
- **No shell injection.** Remote commands are built as argument lists and quoted with `shlex.join`.
- **Errors are reported honestly.** Exit status is checked, so a failed backup is never shown as a success.
- **Timeouts everywhere.** Covers SSH connect, remote commands and HTTP requests.
- **Passwords stay out of logs.** The config object masks the password in its `repr`.

## Quick start

```bash
git clone https://github.com/stormfreaker/ssh-system-admin-tool.git
cd ssh-system-admin-tool
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env        # then edit .env with your lab host and user
ssh-keyscan -H 192.168.56.10 >> ~/.ssh/known_hosts   # trust the host once, on purpose

python -m sshadmin ls
python -m sshadmin backup /home/labadmin/notes.txt
python -m sshadmin           # interactive menu
```

Set up key auth on the target once with `ssh-copy-id labadmin@192.168.56.10`.

### Configuration

| Variable | Required | Default | Notes |
|---|---|---|---|
| `SSHADMIN_HOST` | yes | | Hostname or IP |
| `SSHADMIN_USER` | yes | | Remote username |
| `SSHADMIN_PORT` | no | 22 | |
| `SSHADMIN_KEY_FILE` | no | agent / `~/.ssh` keys | Path to a private key |
| `SSHADMIN_KNOWN_HOSTS` | no | system file | Extra known_hosts file |
| `SSHADMIN_PASSWORD` | no | | Fallback only |

## Project layout

```
sshadmin/
  config.py   settings from env/.env, validation, masked repr
  remote.py   RemoteHost context manager: connect, run, list_home, backup_file
  local.py    local time, local IP, safe web page download
  cli.py      argparse subcommands and the interactive menu
tests/        pytest suite (SSH is mocked, no server needed)
REPORT.md     security review of the original script
```

## Development

```bash
pip install -r requirements-dev.txt
ruff check .
pytest -q
```

CI runs ruff and pytest on Python 3.9 and 3.12 on every push.

## Lab setup

Tested against a VirtualBox Linux VM on a host-only network. Use it only on machines
you own or are allowed to administer.

## License

MIT, see [LICENSE](LICENSE).
