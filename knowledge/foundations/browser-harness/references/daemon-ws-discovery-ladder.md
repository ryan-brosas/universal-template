<!-- capsule-v2 -->
# WS discovery port ladder — which endpoint do you trust when DevToolsActivePort may be stale, 403'd, or 404'd?

**Source:** browser-harness MIT `main@41108b8676d4bdb58b26ab3b079c0b7b0f8f3926`; Codebase Memory `browser-harness`. **Question:** How does a tool find a running Chrome's debug websocket across M144 popups, M147 discovery lockdown, and closed-browser stale files?

## Env override → profile scan w/ liveness → /json/version resolution → fixed-port probes
**Path/Symbol:** `src/browser_harness/daemon.py:get_ws_url` (:211-289) with `_devtools_port_live` (:98-112), `_ws_from_devtools_active_port` (:190-208), `browser_running_for_profile` (:147-163).
**Signature:** `get_ws_url() -> str` raising typed RuntimeErrors (`permission-blocked:` / `chrome-not-running:`).
**Data Shape:** reads `<profile>/DevToolsActivePort` (line1 = port, line2 = ws path) and `<profile>/Local State` (`devtools.remote_debugging.user-enabled`).

### Decisive source
```python
port = active[0].strip(); ws_path = active[1].strip() if len(active) > 1 else ""
# Resolve via /json/version INSTEAD of trusting the stored UUID path:
# a previous browser on the same port leaves a stale path whose WS upgrade 404s.
try: return json.loads(urllib.request.urlopen(
        f"http://127.0.0.1:{port}/json/version", timeout=1).read())["webSocketDebuggerUrl"]
except urllib.error.HTTPError as e:
    if e.code == 403: raise RuntimeError("permission-blocked: ... Allow remote debugging popup ...")
    # Chrome 147+: /json/* disabled on default profile; the file's ws path still works
    if e.code == 404 and ws_path: return f"ws://127.0.0.1:{port}{ws_path}"
...
if not supported_browser_running():     # SingletonLock pid probe (POSIX) /
    raise RuntimeError("chrome-not-running: ...")   # tasklist fallback (Windows)
...
for probe_port in (9222, 9223):         # ALWAYS /json/version, NEVER bare TCP —
                                        # a squatter must not masquerade as Chrome
```

**Flow:** `BU_CDP_WS` literal → `BU_CDP_URL` (30s `/json/version` poll, 403=popup, 404→match DevToolsActivePort by port) → scan profile dirs → liveness-gate stale files (TCP connect on the parsed port) → resolve live WS → grace-window by toggle-state (12s booting-with-toggle vs 3s none) → 9222/9223 probes → typed errors carrying next actions.
**Invariant:** a stale `DevToolsActivePort` file left by a closed browser must NOT route recovery toward a popup that cannot exist; HTTP status codes carry distinct failure semantics (403 human-approval pending vs 404 lockdown fallback); identity checks are protocol-level, never socket-level.
**Probe:** no unit test covers `get_ws_url` directly (needs live Chrome) — coverage caveat: behavior pinned indirectly by `tests/unit/test_admin.py:33/:39` error-classification tests + mirrored probe in `run.py:_local_chrome_listening`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-harness", query: "get_ws_url devtoolsactiveport json/version 403 404", limit: 10, fields: ["name","file","lines"] });
```

## Verdict
Adopt the ladder shape (env → files-with-liveness → protocol-resolution → known ports) for any "find the real thing behind cached hints" problem; adapt profile paths/status handling; omit Browser Use env names. Coverage caveat: live-Chrome path has no upstream unit test.
