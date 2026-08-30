<!-- capsule-v2 -->
# IPC transport boundary — how do two processes talk to a CDP holder without letting every local process drive the browser?

**Source:** browser-harness MIT `main@41108b8676d4bdb58b26ab3b079c0b7b0f8f3926`; Codebase Memory `browser-harness`. **Question:** Which socket/transport does a local automation daemon use per platform, and what makes each side's auth boundary non-forgeable?

## Platform-branched endpoint + token guard
**Path/Symbol:** `src/browser_harness/_ipc.py:serve` (:165-190) with `_server_token` (:32), `connect` (:83-93), `Daemon.handle` token gate (`src/browser_harness/daemon.py:544-550`).
**Signature:** `async def serve(name, handler)` / `def connect(name, timeout=1.0) -> (sock, token|None)`.
**Data Shape:** POSIX: AF_UNIX at `<runtime>/<stem>.sock`; Windows: TCP loopback on an ephemeral port persisted to `<stem>.port` as `{"port": int, "token": hex32B}`. Requests are single-line JSON (`json.dumps(req)+"\n"`), responses single-line JSON.

### Decisive source
```python
# _ipc.py serve(): umask BEFORE bind ⇒ socket is born 0600, no TOCTOU window
old_umask = os.umask(0o077)
try: server = await asyncio.start_unix_server(handler, path=path)
finally: os.umask(old_umask)
_server_token = None                      # POSIX boundary = AF_UNIX perms
...
server = await asyncio.start_server(handler, "127.0.0.1", 0)   # Windows
_server_token = secrets.token_hex(32)     # TCP loopback has NO chmod equivalent
# atomic publish so a concurrent reader never sees a half-written port file
tmp.write_text(json.dumps({"port": port, "token": _server_token}))
os.replace(tmp, pf)

# daemon.py handle(): every request must carry it
expected = ipc.expected_token()
if expected is not None and req.get("token") != expected:
    return {"error": "unauthorized"}
```

**Flow:** client `connect()` → reads port/token file → sends `{..., "token"}` → daemon compares against module-global `_server_token` (set only by `serve()`) → mismatch = `{"error":"unauthorized"}`.
**Invariant:** On Windows EVERY request carries the token (client injects in `request()` :96-106); on POSIX the guard is a structural no-op (`expected_token()` returns None) — porting must keep both halves paired or you get either a broken Windows daemon or dead code confusion. Port file writes are tmp+`os.replace`, never in-place.
**Probe:** `tests/unit/test_ipc.py:11` `test_runtime_stem_uses_bare_name_in_isolated_runtime_dir` pins stem selection; the token contract itself has no direct test (Windows-only path) — coverage caveat: verify by reading `serve()`+`handle()` together.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-harness", query: "_server_token serve start_server token", limit: 10, fields: ["name","file","lines"] });
```

## Verdict
Adopt the dual-boundary pattern (AF_UNIX+umask-0600 vs loopback+bearer token) for any local tool daemon; adapt the runtime-dir env plumbing (`BH_RUNTIME_DIR`/`BH_TMP_DIR` split, shared-vs-isolated stems) to your layout; omit Browser Use-specific log paths. Coverage caveat: Windows branch untested upstream.
