<!-- capsule-v2 -->
# Spawn subprocess bootstrap — what must run AGAIN inside every worker child before the server starts?

**Source:** Uvicorn BSD-3-Clause `main@9ee5694516b01f1d3d6ff9ed38f117fc869ee6ae`; Codebase Memory `ext-uvicorn`. **Question:** Why does the spawn wrapper exist at all, and which two re-initializations happen in the child?

## allow_connection_pickling + spawn context; child: reopen stdin, configure_logging
**Path/Symbol:** `uvicorn/_subprocess.py` — pickling enable :17, spawn context :18, `get_subprocess` :21–48, child entry `subprocess_started` :51–84.
**Signature:** `def get_subprocess(config, target, sockets) -> SpawnProcess` / `def subprocess_started(config, target, sockets, stdin_fileno) -> None`.
**Data Shape:** kwargs dict `{config, target, sockets, stdin_fileno}` passed through spawn pickling — Config must remain picklable (log_config as path/dict, not open handles).

### Decisive source
```python
# :17-18 — module import time: make socket objects survive process borders
multiprocessing.allow_connection_pickling()
spawn = multiprocessing.get_context("spawn")
...
# :74-84 — child side: logging is NOT inherited across spawn
if stdin_fileno is not None:
    sys.stdin = os.fdopen(stdin_fileno)
config.configure_logging()
try:
    target(sockets=sockets)
except KeyboardInterrupt:
    pass   # suppress traceback; parent already expects this end
```

**Flow:** parent calls get_subprocess → stdin fileno captured defensively (`sys.stdin` can be None/without fileno under supervisors → AttributeError/OSError → None) → spawn.Process created with config+target+sockets+stdin_fileno → on start the child reopens stdin for debugger environments, RE-RUNS `configure_logging()` (spawn children inherit no handler state; each worker needs its own formatters/handlers), then invokes target (= Server.run or Multiprocess.Process.target) with the shared sockets.
**Invariant:** `allow_connection_pickling()` must execute in BOTH parent and child before sockets cross — it registers the reduction helpers that make `socket.socket` picklable. Logging setup happens per-child by design, not as an optimization. The KeyboardInterrupt swallow prevents spurious tracebacks from spawn's Popen plumbing.
**Probe:** from the uvicorn checkout root: `bash -c "grep -c 'multiprocessing.allow_connection_pickling()' uvicorn/uvicorn/_subprocess.py"` → 1; `bash -c "grep -c 'config.configure_logging()' uvicorn/uvicorn/_subprocess.py"` → 1.
**Retrieve:** `search_graph {"project":"ext-uvicorn","query":"subprocess spawn stdin fileno configure logging","limit":5,"detail":"ids"}` → resolves `_subprocess` functions line-exact.
**Verdict:** Adopt the two re-inits + defensive stdin capture verbatim for any spawn-based worker family. Adapt context choice ("fork" hosts may skip). Omit win32 signal relays (in Multiprocess capsule).

