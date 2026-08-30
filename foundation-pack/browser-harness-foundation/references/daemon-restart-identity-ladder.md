<!-- capsule-v2 -->
# Daemon restart identity ladder — when may a supervisor SIGTERM the PID it recorded?

**Source:** browser-harness MIT `main@41108b8676d4bdb58b26ab3b079c0b7b0f8f3926`; Codebase Memory `browser-harness`. **Question:** How do you stop/restart a wedged background daemon without ever killing an unrelated process that recycled its PID?

## identify-first shutdown + process-start-time fingerprint fallback
**Path/Symbol:** `src/browser_harness/admin.py:restart_daemon` (:453-533) with `_process_start_time` (:16-104).
**Signature:** `restart_daemon(name=None)`; `_process_start_time(pid) -> str|int|None` (Linux `/proc/<pid>/stat` field 22 · macOS `ps -o lstart=` · Windows GetProcessTimes FILETIME).
**Data Shape:** tracks TWO independent facts: `daemon_pid` (self-reported via `ipc.identify`; None for pre-upgrade daemons whose ping lacks `pid`) and `daemon_alive` (any ping responder).

### Decisive source
```python
daemon_pid   = ipc.identify(name, timeout=5.0)
daemon_alive = daemon_pid is not None or ipc.ping(name, timeout=1.0)
# Snapshot BEFORE waiting: the IPC socket can vanish before the process exits
# (slow remote stop PATCH), so identify() going None ≠ proof of death...
daemon_start = _process_start_time(daemon_pid)
...
for _ in range(75):                       # 75 × 0.2s grace
    try: os.kill(daemon_pid, 0); time.sleep(0.2)
    except (...): break
else:
    # re-verify identity before escalating — EITHER live-IPC match...
    verified_pid = ipc.identify(name, timeout=1.0)
    same_process = verified_pid == daemon_pid or (
        # ...OR start-time fingerprint unchanged (reused PID differs)
        daemon_start is not None
        and _process_start_time(daemon_pid) == daemon_start)
    if same_process:
        os.kill(daemon_pid, signal.SIGTERM)
```

**Flow:** graceful `{"meta":"shutdown"}` IPC → poll up to 15s → escalate to SIGTERM only under a verified identity → always cleanup endpoint + pid file. Unreachable daemon ⇒ cleanup only, NEVER kill-by-pid-file.
**Invariant:** the pid file is never an authorization to signal. The start-time fingerprint keeps the force-kill path alive during the window where the socket is already gone but the process still runs (remote billing stop). Linux parse note: comm may contain spaces/parens — split after the LAST `)` then index field 22.
**Probe:** `tests/unit/test_admin.py:444` `test_restart_daemon_signals_pid_returned_by_identify_not_pid_file`, `:537` `test_restart_daemon_skips_sigterm_if_pid_was_reused_during_wait`, `:582` `test_restart_daemon_sigterms_via_start_time_fingerprint_when_socket_gone`, `:627` `test_restart_daemon_skips_sigterm_when_start_time_changed_during_wait`, `:499` pre-upgrade no-pid shutdown.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-harness", query: "restart_daemon sigterm fingerprint reused pid", limit: 10, fields: ["name","file","lines"] });
```

## Verdict
Adopt the ladder verbatim (graceful-IPC → poll → identity-recheck → signal → cleanup) for any daemon supervisor; adapt the per-OS start-time probes to your platforms; omit the cloud-stop specifics. Five dedicated tests pin every branch — best-tested seam in the repo.
