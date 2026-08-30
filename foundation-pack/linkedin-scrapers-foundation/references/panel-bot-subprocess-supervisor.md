<!-- capsule-v2 -->
# Panel-driven bot subprocess supervisor — how does a local web panel own a scraper child process safely: single-flight start, whole-tree stop, and resumable log tailing?

**Source:** Auto_job_applier_linkedIn MIT `main@0ca5550f8aa80027621cfc17a30fceba05705f84`; Codebase Memory `Auto_job_applier_linkedIn`. **Question:** when a browser control panel runs the bot as a subprocess, what lifecycle contract prevents double-starts, orphaned process trees, and lost logs?

## Single-flight supervisor with group-kill ladder and byte-offset log tail
**Path/Symbol:** `app.py:_bot_proc/_bot_lock` (:156–157), `_is_running` (:165–175), `_terminate` (:185–218), `api_run` (:362–390), `api_stop` (:393–402), `api_logs` (:414–440), `_resolve_port` (:443–462).
**Signature:** `api_run() -> {"running": bool, "pid": int|None, ...}`; `_terminate(proc) -> None`; `api_logs() -> {"content": str, "next_offset": int}`.
**Data Shape:** one module-global `_bot_proc` guarded by a `threading.Lock`; sidecar files `.bot_run.log` (truncated per run) and `.bot_run.pid` (best-effort); log API is a byte-offset cursor protocol (`?offset=N` → content + next_offset).

### Decisive source
```python
# start_new_session makes the child its OWN process-group leader → killpg reaches chromedriver children too
popen_kwargs["start_new_session"] = True        # Windows: CREATE_NEW_PROCESS_GROUP instead
_bot_proc = subprocess.Popen(_bot_command(), stdout=log_file, stderr=subprocess.STDOUT, **popen_kwargs)
...
os.killpg(os.getpgid(proc.pid), signal.SIGTERM)  # graceful group TERM
proc.wait(timeout=5)                             # then escalate
os.killpg(os.getpgid(proc.pid), signal.SIGKILL)  # hard group KILL; Windows: taskkill /F /T /PID
...
if offset > size: offset = 0                     # log was truncated by a NEW run → restart tail
data = log_file.read(); next_offset = offset + len(data)
```

**Flow:** POST /api/run takes the lock → `_is_running()` polls `Popen.poll()` (None = alive; exited = self-clean tracking + PID file) → truncate log ("w" mode) → spawn detached (own session/process-group) → best-effort PID file. POST /api_stop → TERM the group, wait 5 s, KILL the group, remove PID file. UI polls GET /api/logs with last `next_offset`; server seeks, detects truncation (offset > size ⇒ new run started), returns bytes + new cursor.
**Invariant:** at most ONE bot child exists (lock + poll-based liveness, never trust the PID file alone); stopping kills the WHOLE tree because Selenium leaves a chromedriver child; a truncated log never corrupts the tail cursor — it restarts from 0.
**Probe:** `tests/test_app_integration.py::test_status_reports_not_running` + `test_control_panel_and_history_pages_render` (executed this pass inside the repo suite: 17 panel/override tests passed; full suite 56 passed/0 failed/1 live-skipped). The start path itself is only integration-pinned via `_bot_command()`'s isolation seam — coverage caveat: no test spawns a real child.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Auto_job_applier_linkedIn", query: "api_run _terminate api_logs subprocess", limit: 8 });
// → app._terminate app.py :185-218 · app.api_run :363-390 · app.api_logs :415-440 (+ route nodes)
```

## Verdict
Adopt single-flight lock + poll-liveness self-cleanup, detached process-group spawn with TERM→wait→KILL escalation (platform split), truncate-per-run log + byte-offset tail with truncation restart. Adapt PID file to your host's runtime dir and add it to liveness as a hint only. Omit the desktop-oriented pyautogui alerts of the bot itself. Caveat: supervisor behavior source-grounded plus indirect tests; no test drives a real subprocess.
