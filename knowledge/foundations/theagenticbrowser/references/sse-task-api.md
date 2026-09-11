<!-- capsule-v2 -->
# SSE task orchestration — how do you stream progress from backgrounded browser tasks over HTTP without leaking one task into another?

**Source:** TheAgenticBrowser (TheAgentic Community License 1.0) `main@71daa28`; Codebase Memory `mnt-hdd-utopia-inspo-TheAgenticBrowser`. **Question:** How should an API server own per-task orchestrators, push live notifications, and guarantee teardown even when clients disconnect mid-run?

## active_tasks registry + Queue bridge + StreamingResponse finally-cleanup
**Path/Symbol:** `core/server/api_routes.py`:`execute_task` (:97-138, decorator :96), `stream_notifications` (:140-163), `cleanup_task` (:165-183), module attr `active_tasks = {}` (:37). [Pass-4 pin re-verification: ranges previously recorded as :86-121/:124-145/:148-163/:39 were ~11 lines off vs HEAD at the SAME commit `71daa28` — corrected from direct whole-file read 2026-08-26.]
**Signature:** `@app.post("/execute_task") async def execute_task(request, query_model: CommandQueryModel) -> StreamingResponse`; `async def stream_notifications(task_id: str) -> AsyncGenerator[str, None]`.
**Data Shape:** Per-task record `{orchestrator, notification_queue: Queue, start_time}` keyed by client-supplied or uuid4 task_id; duplicate ids rejected HTTP 400. Notifications are `{"message", "type"}` dicts; terminal types `final|error|COMPLETE|ERROR` end the stream.

### Decisive source
```python
orchestrator = Orchestrator(input_mode="API")     # headless + screenshots forced
await orchestrator.async_init()
notification_queue = Queue()
orchestrator.notification_queue = notification_queue   # duck-typed attach
active_tasks[task_id] = {...}
asyncio.create_task(orchestrator.run(query_model.command))
return StreamingResponse(stream_notifications(task_id), media_type="text/event-stream")
...
finally:
    await cleanup_task(task_id)          # runs on completion AND client disconnect
```
The producer side is duck-typed inside the orchestrator: `notify_client` no-ops in GUI_ONLY mode, else `notification_queue.put({"message", "type"})` with a warning when no queue was attached — the API layer never passes callbacks INTO the orchestrator, it attaches a queue attribute after construction.
**Flow:** POST → build+init orchestrator (headless PlaywrightManager fork on input_mode="API") → register → background run() → SSE generator polls get_nowait (100 ms idle sleep) → yields data-lines until terminal type → finally cleanup_task → orchestrator.cleanup() honors session semantics → del from registry.
**Invariant:** Cleanup must live in the STREAM's finally (not the background task) because client disconnects cancel the generator — that is the only reliable death signal. WORKERS=1 is load-bearing: active_tasks is process-local state, so multi-worker uvicorn would split the registry across processes. Orchestrator.cleanup() keeps the browser alive for persistent sessions but stops it when input_mode != GUI_ONLY and no session_id.
**Probe:** No tests (coverage caveat). Graph pin: single Route node in graph (`index_status` node_labels: Route 1); `trace_path --function-name execute_task --direction outbound` reaches cleanup_task via stream_notifications.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-TheAgenticBrowser", query: "stream notifications execute task cleanup", limit: 10, fields: ["name", "file"] });
```

## Verdict
Adopt registry+queue+SSE-finally orchestration for any long-running agent behind HTTP. Adapt terminal-type names and add auth (CORS here is allow-all). Omit nothing in the disconnect path — background-task-side cleanup misses the most common failure mode.
