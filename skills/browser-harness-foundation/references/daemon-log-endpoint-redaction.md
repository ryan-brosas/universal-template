<!-- capsule-v2 -->
# Daemon log endpoint redaction — how do you log which CDP endpoint you attached to without leaking the credential inside its URL?

**Source:** browser-harness MIT `main@6bb1c847fd62638554618e8d1e03247b935ff9cf`; Codebase Memory `browser-harness`. **Question:** A CDP WebSocket URL embeds bearer tokens (`ws://user:secret@host:port/path?token=...`) and provider session paths — what is the minimal reduction that keeps the log useful for debugging topology while leaking nothing?

## Topology-only connection labels
**Path/Symbol:** `src/browser_harness/daemon.py`: `_safe_connection_label` (:187-197); sole consumer `Daemon.start` (:580).

**Signature:** `def _safe_connection_label(url) -> str`.

**Data Shape:** input is any WS/HTTP URL string (possibly garbage); output is `scheme://host[:port]` with IPv6 hosts re-bracketed, or the literal placeholder `<redacted-cdp-endpoint>` when scheme or hostname is missing or parsing raises.

### Decisive source
```python
def _safe_connection_label(url):
    """Log only endpoint topology, never CDP credentials or provider session paths."""
    try:
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.hostname:
            return "<redacted-cdp-endpoint>"
        host = f"[{parsed.hostname}]" if ":" in parsed.hostname else parsed.hostname
        port = f":{parsed.port}" if parsed.port else ""
        return f"{parsed.scheme}://{host}{port}"
    except (TypeError, ValueError):
        return "<redacted-cdp-endpoint>"
```

**Flow:** `Daemon.start` resolves the WS URL via the discovery ladder, then logs `connecting to {_safe_connection_label(url)}` *before* attempting the handshake (:580) — so even the failure path's log line carries only topology. userinfo (credentials), path (provider session ids), and query (tokens) are dropped by construction because only scheme/hostname/port are read back out; malformed input fails closed to the placeholder rather than raising into a never-raise log path. This mirrors the telemetry plane's `_cdp_hostname` reduction (see telemetry-detached-optout): both reduce URLs to authority-only before anything leaves the process, but this one keeps the port because "which endpoint" is exactly what daemon-log debugging needs.

**Invariant:** The daemon log file persists on disk in a shared runtime dir; no transform may run on it later, so the label must be safe at write time. Never log `str(e)` from a handshake exception that interpolates the full URL — pair the redacted connect log with error messages that quote only failure causes (see `start()`'s RuntimeError ladder :587-599).

**Probe:** `tests/unit/test_daemon.py::test_safe_connection_label_removes_credentials_paths_and_queries` (:8-21) parametrizes: `"ws://openclaw-internal:secret@127.0.0.1:18792/devtools/browser/id?token=x"` → `"ws://127.0.0.1:18792"`; `"wss://provider.example/session/private-id?token=secret"` → `"wss://provider.example"`; `"wss://[::1]:9222/devtools/browser/id"` → `"wss://[::1]:9222"`; `"not-a-url"` → `"<redacted-cdp-endpoint>"`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.trace_path({ project: "browser-harness", function_name: "_safe_connection_label", direction: "inbound", depth: 1 });
```
Returns exactly one caller: `Daemon.start` (verified live this pass), proving the redaction sits on every connect log regardless of discovery-ladder rung.

## Verdict
Adopt write-time authority-only URL reduction for any log that can carry a credentialed endpoint, plus the fail-closed placeholder for unparseable input; adapt the placeholder string and whether to keep the port; omit nothing else — the function is 11 lines and complete. Coverage caveat: none — direct parametrized unit test exists at this pin and runs GREEN ambient.
