<!-- capsule-v2 -->
# Detached-daemon spawn + NDJSON request envelope — how do you launch a helper daemon that survives its parent terminal, and what exact wire contract do one-shot clients speak?

**Source:** browser-harness MIT `main@41108b8676d4bdb58b26ab3b079c0b7b0f8f3926`; Codebase Memory `browser-harness`. **Question:** Which Popen flags truly detach a background daemon on each OS, and how must a client frame, send, and read a single JSON request without deadlocking or mis-parsing?

## Platform-branched spawn flags + newline-framed one-shot RPC
**Path/Symbol:** `src/browser_harness/_ipc.py:spawn_kwargs` (:72-80), `connect` (:83-93), `request` (:96-106).
**Signature:** `spawn_kwargs() -> dict` (Popen kwargs); `connect(name, timeout=1.0) -> (sock, token|None)`; `request(c, token, req) -> dict`.
**Data Shape:** POSIX: AF_UNIX socket path + no token; Windows: TCP 127.0.0.1 port from a JSON port file carrying `{port, token}` — every request must merge `token` into its body.

### Decisive source
```python
if IS_WINDOWS:
    # CREATE_NO_WINDOW ... CREATE_NEW_PROCESS_GROUP: daemon doesn't receive Ctrl-C
    # sent to the parent terminal. DETACHED_PROCESS is intentionally omitted:
    # it overrides CREATE_NO_WINDOW, causing Windows to allocate a fresh console.
    return {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW}
return {"start_new_session": True}
```
```python
if token: req = {**req, "token": token}
c.sendall((json.dumps(req) + "\n").encode())
data = b""
while not data.endswith(b"\n"):
    chunk = c.recv(1 << 16)
    if not chunk: break
    data += chunk
return json.loads(data or b"{}")
```

**Flow:** Spawn: POSIX detaches via one `start_new_session`; Windows combines new-process-group + no-window and deliberately skips DETACHED_PROCESS (the Win32 override would re-allocate a console for console-subsystem python.exe). Request: copy-merge token on Windows only → send JSON+`\n` in ONE sendall → accumulate ≤64 KiB chunks until trailing `\n` or EOF → parse; empty stream parses to `{}` instead of raising.
**Invariant:** Detachment must survive the parent's Ctrl-C (new process group / new session), not merely outlive the parent. The `\n` framing terminator doubles as the flush/commit marker; EOF without it means "peer vanished" and degrades to `{}`, never an exception in the read loop. Token presence is platform-gated at BOTH connect and request layers — callers cannot forget it because request() injects it. Liveness of a discovered endpoint is NOT proven by connect success — that's ping()'s pong-shape defense (see `daemon-ping-identity-defense`).
**Probe:** Executed against pinned source: posix `spawn_kwargs()` → `{'start_new_session': True}`; socketpair roundtrip with a 200 KB NDJSON response → fully received through multi-chunk recv loop (200000 chars); FakeSock capture shows `{meta:'ping'}` + truthy token → wire body carries `"token":"tok123"`; empty stream → `{}` (no exception). No direct unit test covers spawn_kwargs/request — coverage caveat; anchors verified at source :72-106.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-harness", query: "spawn detach request token newline ipc", file_pattern: "*.py", limit: 10 });
```

## Verdict
Adopt the flag pair semantics (process-group/session detachment ≠ window suppression; know your platform's flag overrides), single-sendall newline framing, chunked recv-until-newline, and central token injection. Adapt socket paths/port-file formats and the 1s default timeout to your host. Omit Windows branches only if you genuinely never target Windows — the AF_UNIX gate exists precisely because uv-Python there lacks the family.
