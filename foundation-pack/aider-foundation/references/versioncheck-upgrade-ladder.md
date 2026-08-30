<!-- capsule-v2 -->
# Version-check nagger — PyPI latest-fetch with install-channel-aware upgrade commands

**Source:** Aider Apache-2.0 `main@5dc9490bb35f9729ef2c95d00a19ccd30c26339c`; Codebase Memory project `aider`. **Question:** How does a pip-installed CLI check for updates and print the RIGHT upgrade command for whatever way the user installed it?

## One PyPI fetch; three upgrade ladders chosen by executable path (uv tool / pipx / pip); just_check returns exit code instead of nagging
**Path/Symbol:** `aider/versioncheck.py`: `check_version(io, just_check=False, verbose=False)` (:14), PyPI fetch `https://pypi.org/pypi/aider-chat/json` (:31, 1s timeout, silent-fail on any error), `install_from_main_branch(io)` (:58), `install_upgrade(io)` (:86-112), textwrap-dedented banner text.
**Signature:** `just_check=True` returns bool(update_available) — main.py maps it to exit codes 0/1 (:722-725) so CI can gate on currency; the interactive path prints a banner and STAYS SILENT afterwards (no per-run repeat thanks to `~/.aider/check-update` ctime file written on each check).
**Data Shape:** upgrade-command ladder: `"uv" in str(sys.executable)` → `uv tool upgrade aider-chat`; `.venv` in executable or pipx absent → `python -m pip install -U aider-chat`; else → `pipx upgrade aider-chat`; main-branch install uses `python -m pip install --upgrade git+...@main` after confirming.

### Decisive source
```python
def install_upgrade(io):
    if "uv" in sys.executable:
        cmd = "uv tool upgrade aider-chat"
    elif ".venv" in sys.executable:
        cmd = "python -m pip install -U aider-chat"
    elif "pipx" in str(Path(sys.executable)):
        cmd = "pipx upgrade aider-chat"
    else:
        cmd = "python -m pip install -U aider-chat"
...
if (update_check_freq > elapsed) and not verbose:
    return True      # ctime-based daily throttle
```

**Flow:** launch (post-config, pre-model) → throttle via check-update file mtime/ctime (24h) → fetch latest from PyPI (network errors swallowed: update-checking must never break launch) → compare tuple-parsed versions → print banner with channel-correct command → optionally offer to run it.
**Invariant:** update checks are fail-open and throttled — a dead network or rate-limited PyPI never delays or alarms the user; the command suggestion is derived from the RUNNING interpreter path, not $PATH guessing, so uv-managed users never get pip advice that would break their install isolation.
**Probe:** NO dedicated upstream test file exists for versioncheck.py (flows covered indirectly by `tests/basic/test_main.py`; source-pinned caveat). Deterministic anchors: `grep -nF 'uv tool upgrade' aider/versioncheck.py` → exactly one site; `grep -nF 'check-update' aider/versioncheck.py | head -2`.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "aider", query: "check_version install_upgrade", limit: 3 });
// resolves versioncheck.py functions line-exact
```

## Verdict
Adopt the interpreter-path-derived upgrade ladder verbatim for any distributed Python CLI; adapt package names. The ctime throttle + fail-open fetch pair is what makes this polite — porters who fetch every launch add seconds and a network dependency to startup.
