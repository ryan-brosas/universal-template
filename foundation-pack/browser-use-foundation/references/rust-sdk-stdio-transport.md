<!-- capsule-v2 -->
# RustSdkClient stdio JSON-RPC transport — how do you talk to a subprocess agent-core over line-delimited JSON-RPC without deadlocking or losing notifications?

**Source:** browser-use MIT `main@3c989dc`; Codebase Memory `browser-use`. **Question:** what does a minimal stdio JSON-RPC client need so request/response correlation survives large lines, process death, and event notifications interleaved with responses?

## Connected graph-selected seam
**Path/Symbol:** `browser_use/beta/service.py:323` `class RustSdkClient` (whole class :323-529); `RustSdkJsonRpcError` (:314); `_fail_all` (:520).
**Signature:** `RustSdkClient(command: list[str], env: dict[str,str])` with `async start()`, `async call(method, params) -> Any`, `async close()`; internals `_read_stdout()`, `_handle_stdout_line(raw: bytes) -> bool`, `_handle_message(msg)`.
**Data Shape:** requests `{jsonrpc:'2.0', id:int, method, params}` newline-delimited on stdin; responses correlate by integer `id`; notifications (`method` present, no `id`) with method ∈ {`agent.event`, `agent.projected_event`} are queued; env knobs `BROWSER_USE_SDK_STREAM_LIMIT_BYTES` (default 64MiB asyncio stream limit), `BROWSER_USE_SDK_READ_CHUNK_BYTES` (1MiB), `BROWSER_USE_SDK_MAX_LINE_BYTES` (512MiB).

### Decisive source
```python
# manual newline framing over raw read(chunk): asyncio streams have no readline
# that survives a 70KB single line when limit=4096 — so read chunks into a
# bytearray and split on b'\n' yourself:
chunk = await self.process.stdout.read(self.read_chunk_size)
buffer.extend(chunk)
while (newline_index := buffer.find(b'\n')) >= 0:
    ... self._handle_stdout_line(bytes(buffer[:newline_index]))
if len(buffer) > self.max_line_bytes:   # unbounded-line kill switch
    self._fail_all(BetaAgentError(f'Rust SDK JSON-RPC line exceeded {self.max_line_bytes} bytes without newline'))
# writes serialized under a lock; per-request future registered BEFORE drain:
async with self._write_lock:
    self._pending[request_id] = future
    self.process.stdin.write((json.dumps(request) + '\n').encode('utf-8'))
    await self.process.stdin.drain()
# reader death fails EVERY pending future with stderr tail attached:
finally:
    if self._pending:
        detail = '\n'.join(self.stderr_lines[-20:])
        message = 'Rust SDK server exited before responding'
        ...
        self._fail_all(BetaAgentError(message))
```

**Flow:** `call()` → lazy `start()` → register future under `_write_lock` → drain → await future; reader task frames stdout lines, dispatches notifications to `notifications` list (ring of 2000) + `notification_queue`, resolves/rejects response futures by int id (`future.done()` check makes late duplicates harmless); `close()` closes stdin, terminate→wait(2s)→kill ladder, cancels reader tasks, `_fail_all` remaining futures. Stderr is drained into a 500-line ring purely for error context.
**Invariant:** every pending future MUST eventually resolve or reject even if the child dies silently (the finally-block `_fail_all`) — otherwise callers hang forever; malformed JSON or non-object messages fail all pending calls rather than being skipped; notification handling never blocks the response path.
**Probe:** `tests/ci/test_beta_agent.py:3326` `test_rust_sdk_client_reads_large_json_rpc_lines` — spawns real python child emitting a 70,000-char payload with `BROWSER_USE_SDK_STREAM_LIMIT_BYTES=4096`, asserts full result round-trips (proves manual framing beats stream readline); `tests/ci/test_beta_agent.py:3348` `test_rust_sdk_client_queues_agent_notifications_before_response`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-use", query: "RustSdkClient call _read_stdout _fail_all", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the chunk-and-split framing + pending-future map + fail-all-on-reader-death trio verbatim for any subprocess JSON-RPC peer; adapt the env knob names and ring sizes to your host; omit the browser-use-terminal-specific method vocabulary (`agent.event`/`agent.projected_event`) unless bridging the same Rust core.
