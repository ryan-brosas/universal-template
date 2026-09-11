<!-- capsule-v2 -->
# Browser-kind self-report chain — how does a CLI attribute telemetry to the right browser mode (cloud/cdp/local) when the daemon, not the client, knows the truth?

**Source:** browser-harness MIT `main@6bb1c847fd62638554618e8d1e03247b935ff9cf`; Codebase Memory `browser-harness`. **Question:** The daemon derives its browser mode from the environment it was *born* with — how does that value travel derivation → wire → validated consumption without a stale or hostile client being able to forge it?

## Import-time derivation + ping-envelope piggyback + whitelist-or-None consumers
**Path/Symbol:** `src/browser_harness/daemon.py`: `BROWSER_KIND` (:91), ping arm in `Daemon.handle` (:626); `src/browser_harness/admin.py`: `daemon_browser_kind` (:189-204); `src/browser_harness/run.py`: `_telemetry_command` (:114-132), `_telemetry_browser` (:226-234), `main` emission (:237-298).

**Signature:** `BROWSER_KIND = "cloud" if REMOTE_ID else ("cdp" if (os.environ.get("BU_CDP_WS") or os.environ.get("BU_CDP_URL")) else "local")`; `def daemon_browser_kind(name=None)`; `def _telemetry_browser(task)`.

**Data Shape:** vocabulary is exactly `{"cloud", "cdp", "local"}`; every consumer normalizes anything else — including absence — to `None`, and `None` means "no attribution", never an error.

### Decisive source
```python
    c = None
    try:
        c, token = ipc.connect(name or NAME, timeout=1.0)
        response = ipc.request(c, token, {"meta": "ping"})
        kind = response.get("browser_kind") if isinstance(response, dict) else None
        return kind if kind in {"cloud", "cdp", "local"} else None
    except (FileNotFoundError, ConnectionRefusedError, TimeoutError, socket.timeout, OSError, ValueError):
        return None
    finally:
        if c:
            c.close()
```

**Flow:** derivation happens once at daemon import from its own process env (`BU_BROWSER_ID` ⇒ cloud; else `BU_CDP_WS`/`BU_CDP_URL` ⇒ cdp; else local) — the *daemon's* env, not the caller's, because autospan may have created the cloud browser in a different process. The value piggybacks on the existing liveness ping (`{"pong": True, "pid": …, "browser_kind": BROWSER_KIND}`) so no extra round trip exists. Consumer side: `admin.daemon_browser_kind` asks the ping with a 1s timeout and returns the field only under a closed whitelist; `None` deliberately covers BOTH unreachable-daemon AND legacy-daemon-without-the-field (forward compatibility across versions). Attribution gates: `_telemetry_browser(task)` returns None unless a task ran AND telemetry is enabled; `_telemetry_command` classifies argv into a closed command vocabulary (`script/help/version/doctor/update/reload/debug-clicks/{auth,skill,mac-approve,recordings,telemetry,video}/usage`); `run.main` emits exactly one `capture_cli_event` per exit path (SystemExit :253-268, Exception :269-283, success :287-298) so no path double-reports.

**Invariant:** Never trust client-side classification of a resource the client didn't create; never let "unknown" collapse into a default guess — `None` is its own answer (the admin self-heal plane later treats None as cloud for cleanup disposition precisely because unclassified daemons may be billable — see admin-selfheal-ladder). Consumers must be total: whitelist-or-None, never raise.

**Probe:** Deterministic probes (lane precedent): subprocess env-matrix importing the pinned module asserts the derivation precedence; empty-runtime-dir probe drives `daemon_browser_kind` down its `None` path; pure-function argv matrix over `_telemetry_command`; disabled-telemetry probe pins `_telemetry_browser` gating. Envelope layer: `tests/unit/test_ipc.py:100-128` read (pong-exactly-True; non-dict payloads → False, not raise).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.trace_path({ project: "browser-harness", function_name: "daemon_browser_kind", direction: "inbound", depth: 2 });
```
Resolves the consumers (`ensure_daemon` stale-disposition :356-366, run attribution); `get_code_snippet` on `admin.daemon_browser_kind` returns :189-204 byte-identical above (verified live this pass at the post-drift pin).

## Verdict
Adopt producer-side env derivation frozen at daemon birth, piggybacking derived facts on existing liveness envelopes, and closed-vocabulary/whitelist-or-None consumption; adapt the vocabulary and env names; omit Browser Use specifics. Coverage caveat: no direct unit suite covers the full derivation→wire→attribution chain (BM25 over tests surfaces only ping-envelope tests); deterministic probes substitute per lane precedent.
