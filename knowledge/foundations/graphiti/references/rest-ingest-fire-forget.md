<!-- capsule-v2 -->
# Fire-and-forget REST ingest — 202 queue with drain-on-stop loss window

**Source:** graphiti MIT `main@993e081a`; Codebase Memory `graphiti`. **Question:** what is the minimal async-ingest contract for an HTTP API whose extraction work is too slow to serve inline, and where does it lose data?

## Connected graph-selected seam
**Path/Symbol:** `server/graph_service/routers/ingest.py` — `AsyncWorker` (:13-35), module singleton `async_worker` (:38), router-owned `lifespan` (:41-48), `POST /messages` (:51-70).
**Signature:** `AsyncWorker.queue: asyncio.Queue` of zero-arg callables; `worker()` loop awaits `queue.get()` then `await job()`; jobs built as `partial(add_messages_task, m)` closing over request-scoped values.
**Data Shape:** `AddMessagesRequest{group_id, messages[]}` → one task PER message (per-message granularity, not batched); response is immediate `Result(message='Messages added to processing queue', success=True)` with status **202 Accepted**.

### Decisive source
```python
# ingest.py :18-25 + :67-70 — enqueue-only endpoint; single serial consumer:
async def worker(self):
    while True:
        try:
            print(f'Got a job: (size of remaining queue: {self.queue.qsize()})')
            job = await self.queue.get()
            await job()
        except asyncio.CancelledError:
            break
...
for m in request.messages:
    await async_worker.queue.put(partial(add_messages_task, m))
return Result(message='Messages added to processing queue', success=True)
#
# :30-35 — stop order matters: cancel consumer FIRST, then drop leftovers:
async def stop(self):
    if self.task:
        self.task.cancel(); await self.task
    while not self.queue.empty():
        self.queue.get_nowait()
```

**Flow:** POST /messages validates via pydantic → enqueues N closures → returns 202 before any LLM work → lone worker executes them strictly serially in arrival order (no concurrency cap needed because there is exactly one consumer; the unbounded queue IS the backpressure policy: none) → episode_body per message is `f'{m.role or ""}({m.role_type}): {m.content}'`.
**Invariant:** (1) 202 means 'queued', NOT 'persisted' — clients must poll GET /episodes/{group_id} (the live test does exactly this); (2) the queue is process-local and UNBOUNDED: crash or deploy drops queued jobs with zero durability, and stop() actively drains them — this is the deliberate opposite of mcp_server's durable per-group SQLite-backed queue (see `mcp-queue-service` capsule): same product need, opposite durability point chosen per surface; (3) jobs are closures capturing the request DTO, so nothing about the request needs to outlive the connection except queued memory; (4) `/clear` and DELETE endpoints bypass the queue and act synchronously, so a clear racing queued adds can interleave.
**Probe:** `.venv/bin/python - <<'PY'` style import probe executed this pass (probe P1 in verification.md): started AsyncWorker, ran one enqueued job to completion, called stop(), asserted `queue.empty()` is True afterwards → True/True. Direct tests: server/tests/test_live_falkordb_int.py exercises POST /messages end-to-end but requires live FalkorDB + OPENAI_API_KEY (skipped in unit runs) — coverage caveat.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase-memory.search_graph({ project: "graphiti", query: "AsyncWorker queue worker lifespan add_messages", limit: 10 });
```

## Verdict
Adopt the closure-per-item 202 pattern when callers can tolerate at-most-once ingest and you want zero infra (no broker, no table); port the durable MCP queue instead when the caller cannot re-send. Never present this shape as reliable delivery — the loss window is the design.
