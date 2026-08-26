<!-- capsule-v2 -->
# Delta coalescing — how do you throttle high-frequency stream deltas into bounded socket writes without reordering or losing a type?

**Source:** open-webui "Open WebUI License" (BSD-3-Clause base + branding condition; citations-only) `main@01f4282f1ffe0d6212f58d3afbeae21fffd0c4be`; Codebase Memory `open-webui`. **Question:** When a provider streams hundreds of content deltas per second over socket.io, how do I batch them safely while keeping tool-call and content events in order?

## Single pending slot keyed by delta type
**Path/Symbol:** `backend/open_webui/utils/middleware.py:queue_pending_delta_data` / `flush_pending_delta_data` (closures inside `stream_body_handler`, 4179-4216).
**Signature:** `async def queue_pending_delta_data(delta_data: dict, delta_type: str)`; `async def flush_pending_delta_data(threshold: int = 0)`.
**Data Shape:** one pending slot: `last_delta_data: dict | None`, `last_delta_type: 'content' | 'tool_call' | None`, `delta_count: int`. The queued payload is a FULL-STATE snapshot — `processed_data = {'output': full_output()}` (middleware.py 4333-4335) merged with response metadata — never an incremental fragment, so replacing the slot loses nothing. Flush emits `{'type': 'chat:completion', 'data': last_delta_data}`.

### Decisive source
```python
delta_chunk_size = max(
    CHAT_RESPONSE_STREAM_DELTA_CHUNK_SIZE,
    int(metadata.get('params', {}).get('stream_delta_chunk_size') or 1),
)
...
if last_delta_type and last_delta_type != delta_type:
    await flush_pending_delta_data()

delta_count += 1
last_delta_data = delta_data
last_delta_type = delta_type

if delta_count >= delta_chunk_size:
    await flush_pending_delta_data(delta_chunk_size)
```
(middleware.py 4180-4216)

**Flow:** queueing a delta of a DIFFERENT type flushes the pending slot first (type switch is the ordering boundary) → increment count, replace slot contents (latest wins) → at `delta_chunk_size`, flush. Three forced flush points guarantee nothing strands in the slot: any non-delta event flushes before it is processed (`middleware.py 4296-97`), and end-of-stream flushes once (`4821`). The per-request `params.stream_delta_chunk_size` can only RAISE the floor above the env default via `max()` — a client cannot set it below the server's configured batch size.
**Invariant:** deltas of the same type may coalesce (only the latest payload survives), but no delta of type B is ever emitted before an earlier queued delta of type A, and every non-delta event observes an empty pending slot.
**Probe:** no upstream tests exist at this pin (zero test files repo-wide — recorded block). Deterministic anchors: `grep -n "last_delta_type != delta_type" backend/open_webui/utils/middleware.py` → 4208; `grep -n "await flush_pending_delta_data()" backend/open_webui/utils/middleware.py` → exactly 4209 (type switch), 4297 (pre-non-delta), 4821 (end-of-stream); `grep -n "CHAT_RESPONSE_STREAM_DELTA_CHUNK_SIZE = " backend/open_webui/env.py` → 996 (default `'1'`, parse-fail fallback to 1 at 999-1004).

## Get live surrounding code
**Retrieve:** `queue_pending_delta_data`/`flush_pending_delta_data` are CLOSURES inside `stream_body_handler`, not graph nodes — a naive name query MISSES (observed: drifts to unrelated `flush` functions). Target the enclosing handler:
```ts
await mcp.codebase_memory.search_graph({ project: "open-webui", query: "streaming_chat_response_handler tool call iterations while loop", limit: 10, fields: ["signature", "name", "file"] });
```
→ resolves `streaming_chat_response_handler` 3750-5653; read lines 4177-4216 plus flush sites 4209/4297/4821 from source.

## Verdict
Adopt the single-slot keyed-by-type coalescer with its three flush guarantees, the server-floor `max()` arithmetic, and above all the cumulative-snapshot payload — because each queued item is `{'output': full_output()}`, latest-wins slot replacement is lossless and clients are idempotent under coalescing. Adapt the emitted event shape (`chat:completion`) and where counts come from. Omit open-webui's specific delta types. Coverage caveat: middleware.py is graph-clean but has no upstream test; claims pinned by direct source reads at lines cited above (including the 4333-4335 snapshot read that distinguishes this from naive delta dropping).
