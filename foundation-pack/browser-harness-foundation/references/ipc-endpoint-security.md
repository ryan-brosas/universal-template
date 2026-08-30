<!-- capsule-v2 -->
# Endpoint discovery + stale-proof liveness — how do you enumerate every running daemon and never mistake a port thief for yours?

**Source:** browser-harness MIT `main@41108b8676d4bdb58b26ab3b079c0b7b0f8f3926`; Codebase Memory `browser-harness`. **Question:** How does tooling find daemons across isolation modes, and what proves an endpoint is really our daemon?

## Two-mode enumeration + handshake liveness
**Path/Symbol:** `src/browser_harness/_ipc.py:_runtime_stem/_check` (:35-48); `src/browser_harness/admin.py:_daemon_endpoint_names/daemon_alive` (:207-223, :183-186).
**Signature:** `_daemon_endpoint_names() -> list[str]`; `daemon_alive(name=None) -> bool`.
**Data Shape:** Caller-supplied isolated dir (`BH_RUNTIME_DIR`, not shared) ⇒ files use bare `bu` stem — one daemon per dir, discovery returns `[NAME]` iff `bu.sock/.port` exists; shared dir ⇒ `bu-<NAME>` stems discovered by globbing `bu-*.{sock,port}`, names extracted by prefix/suffix strip then validated against `[A-Za-z0-9_-]{1,64}` (invalid silently skipped).

### Decisive source
```python
def daemon_alive(name=None):
    # Ping handshake (not a bare connect) so a stale .port file + port reuse
    # after a daemon crash doesn't make us mistake an unrelated listener for ours.
    return ipc.ping(name or NAME, timeout=1.0)
```

**Flow:** glob endpoints → validate names → per-name `connection_status` probe keeps only healthy daemons (`browser_connections`/`active_browser_connections`) → liveness ALWAYS via full ping round-trip, never bare connect.
**Invariant:** A successful TCP connect proves nothing — after a crash any process can grab the port; only `{"pong":true}` identifies our daemon (mirrored at the Chrome layer: `/json/version` probe instead of bare TCP); stem choice is load-bearing because the filename must not leak instance names across isolated dirs.
**Probe:** `tests/unit/test_admin.py:51-94` — glob skips `bu-invalid.name.sock`/`not-bu-default.sock`; isolated mode returns local name only when sock exists; shared mode discovers named sockets while ignoring stale bare-stem endpoints; `:97-134` counts only daemons whose CDP connection answers without error.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-harness", query: "endpoint names discover runtime stem", limit: 10, fields: ["signature", "file"] });
```

## Verdict
Adopt handshake-based liveness wherever processes are addressed by port/socket file; adopt regex-validated name extraction for multi-instance discovery. Adapt stems/env names. Omit the isolated-vs-shared duality if you always isolate.
