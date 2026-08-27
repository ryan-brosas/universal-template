<!-- capsule-v2 -->
# ensure_daemon self-heal ladder — how does a CLI turn opaque daemon failures into user actions, retry, and decide HOW to replace a stale daemon without orphaning a billable browser?

**Source:** browser-harness MIT `main@6bb1c847fd62638554618e8d1e03247b935ff9cf`; Codebase Memory `browser-harness`. **Question:** When the daemon won't come up, how does the caller classify WHY from a log tail, pick exactly one recovery action per failure class — and how does it choose between plain restart and strict billable cleanup for a stale daemon?

## Log-tail classification → one-shot recoveries → kind-keyed stale disposition → errors that ARE instructions
**Path/Symbol:** `src/browser_harness/admin.py`: `ensure_daemon` (:340-451; CDP liveness probe :343-355; **stale disposition keyed by self-reported browser kind :356-366**), spawn/retry loop (:368+); classifiers `_needs_chrome_remote_debugging_prompt`/`_needs_chrome_permission_popup`/`_chrome_not_running` (unchanged positions <340); `_log_tail` (:135-139); inspect pair `_open_chrome_inspect` (:1001-1019) / `_open_chrome_inspect_once` (:1025-1039) with `INSPECT_REOPEN_TTL = 180.0` (:1022).
**Signature:** `ensure_daemon(wait=60.0, name=None, env=None)`; up to 3 spawn attempts.
**Data Shape:** daemon writes human-readable log lines; sentinel prefixes: `handshake-wait:` (parked on popup), `permission-blocked:`, `chrome-not-running:`.

### Decisive source
```python
        browser_kind = daemon_browser_kind(name)
        if browser_kind in {"cloud", None}:
            # A stale Cloud daemon still owns a billable browser. Its shutdown
            # handler stops that browser before acknowledging, and stays alive
            # when the Cloud stop fails so a later call can retry cleanup. Treat
            # an unknown kind the same way: the health failure that made the
            # daemon stale may also prevent classification, and replacing an
            # unclassified daemon best-effort could orphan a Cloud browser.
            stop_remote_daemon(name or NAME)
        else:
            restart_daemon(name)
```

**Flow:** ping-alive ⇒ still verify with a REAL CDP call (`Target.getTargets`, twice 0.5s apart, via IPC — stale daemons answer meta:* but have a dead WS) → if verification fails, ask the daemon's ping envelope for its self-reported `browser_kind`: `cloud` OR `None` ⇒ `stop_remote_daemon` (strict cleanup path: the shutdown handler stops the billable browser before acknowledging and keeps the daemon alive as a retryable cleanup authority when the stop fails); known-local kinds (`cdp`/`local`) ⇒ plain `restart_daemon` → then spawn detached w/ stderr→logfile → poll ping + process exit + log tail → classify once per class (browser-launch / inspect-open / permission-blocked) → typed RuntimeError whose text is the instruction to the calling agent.
**Invariant:** every recovery action fires AT MOST ONCE across attempts (flags `launched_browser`/`opened_inspect`) — infinite popup loops otherwise; alive-but-useless daemons must be detected by protocol probes, not pings alone; an UNCLASSIFIABLE daemon must be treated as potentially billable (None-is-cloud fail-safe) because the same failure that staled it may have broken its self-report; TTL marker (`INSPECT_REOPEN_TTL=180s`) prevents inspect-tab spam across invocations.
**Probe:** `tests/unit/test_admin.py::test_handshake_timeout_needs_chrome_remote_debugging_prompt` (:119), `::test_handshake_403_needs_chrome_remote_debugging_prompt` (:125), `::test_stale_websocket_does_not_open_chrome_inspect` (:131); full ladder itself has no direct test (spawns processes) — coverage caveat recorded; the kind-keyed disposition is exercised only via `daemon_browser_kind`'s own None-path probe (empty runtime dir).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-harness", query: "ensure_daemon handshake-wait chrome not running permission", limit: 10, fields: ["name","file","lines"] });
```

## Verdict
Adopt the pattern (sentinel-prefixed logs → substring classification → one-shot recovery flags → protocol-probe staleness checks → kind-keyed replacement strictness → errors-as-instructions) for any tool with a supervised background process that may own metered resources; adapt sentinels/actions/kind vocabulary; omit Chrome specifics.
