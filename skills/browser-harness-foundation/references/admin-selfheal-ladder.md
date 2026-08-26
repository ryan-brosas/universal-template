<!-- capsule-v2 -->
# ensure_daemon self-heal ladder — how does a CLI turn opaque daemon failures into user actions and retry?

**Source:** browser-harness MIT `main@41108b8676d4bdb58b26ab3b079c0b7b0f8f3926`; Codebase Memory `browser-harness`. **Question:** When the daemon won't come up, how does the caller classify WHY from a log tail and pick exactly one recovery action per failure class?

## Log-tail classification → one-shot recoveries → typed errors that ARE instructions
**Path/Symbol:** `src/browser_harness/admin.py:ensure_daemon` (:340-441) with classifiers `_needs_chrome_remote_debugging_prompt` (:142), `_needs_chrome_permission_popup` (:161), `_chrome_not_running` (:167); `_log_tail` (:135).
**Signature:** `ensure_daemon(wait=60.0, name=None, env=None)`; up to 3 spawn attempts.
**Data Shape:** daemon writes human-readable log lines; special sentinel prefixes: `handshake-wait:` (parked on popup), `permission-blocked:`, `chrome-not-running:`.

### Decisive source
```python
if local and not launched_browser and _chrome_not_running(msg):
    launched_browser = True                       # ONE-SHOT flag per class
    restart_daemon(name)
    if not _launch_browser(): raise RuntimeError("chrome-not-running: ... ask ...")
    ...boot-wait loop...; continue                # retry spawn after launch
if local and not opened_inspect and _needs_chrome_remote_debugging_prompt(msg):
    opened_inspect = True
    if remote_debugging_user_enabled(): raise permission-blocked(...)
    restart_daemon(name); _open_chrome_inspect_once()   # TTL-gated tab open
    raise RuntimeError(f"remote-debugging-setup: opened chrome://inspect ... ask the user to {todo} ...")
raise RuntimeError(msg or f"daemon {name} didn't come up -- check {log}")
```
Sentinels are matched by SUBSTRING against lowercased messages; `permission-blocked` short-circuits everything because only a human can clear it.

**Flow:** ping-alive ⇒ still verify with a REAL CDP call (`Target.getTargets`, twice, via IPC — stale daemons answer meta:* but have a dead WS) else restart → spawn detached w/ stderr→logfile → poll ping + process exit + log tail → classify once per class (browser-launch / inspect-open / permission-blocked) → typed RuntimeError whose text is the instruction to the calling agent.
**Invariant:** every recovery action fires AT MOST ONCE across attempts (flags `launched_browser`/`opened_inspect`) — infinite popup loops otherwise; alive-but-useless daemons must be detected by protocol probes, not pings alone; TTL marker (`INSPECT_REOPEN_TTL=180s`) prevents inspect-tab spam across invocations.
**Probe:** `tests/unit/test_admin.py:33/:39` classifier matrix (timeout/403 need prompt), `:45` `test_stale_websocket_does_not_open_chrome_inspect`; full ladder itself has no direct test (spawns processes) — coverage caveat recorded.
**Coverage caveat:** the spawn/retry loop is exercised only indirectly via classifier unit tests.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-harness", query: "ensure_daemon handshake-wait chrome not running permission", limit: 10, fields: ["name","file","lines"] });
```

## Verdict
Adopt the pattern (sentinel-prefixed logs → substring classification → one-shot recovery flags → errors-as-instructions) for any tool with a supervised background process; adapt sentinels/actions; omit Chrome specifics.
