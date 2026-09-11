<!-- capsule-v2 -->
# ModelRequestNode streaming handoff — cooperative task/consumer stream coordination

**Source:** pydantic-ai (MIT) `main@b3cdbc96796f0294f1ac6943cdba70d14af8a0ef`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** When a porter streams a model request through capability middleware, how does the node hand off the open stream between a background task (running `wrap_model_request`) and the consuming coroutine without leaking the task or double-closing the stream?

## ModelRequestNode.stream cooperative handoff
**Path/Symbol:** `pydantic_ai/_agent_graph.py:ModelRequestNode` (1106-1354), `stream` (1140-1354), `_streaming_handler` (1186-1217).
**Signature:** `ModelRequestNode.stream(ctx) -> AsyncGenerator[AgentStream]`; `run(ctx) -> CallToolsNode | ModelRequestNode`.
**Data Shape:** `stream_ready`/`stream_done` are `asyncio.Event`s; `agent_stream_holder` is a one-element list; `wrap_task` is the background `wrap_model_request` task.

### Decisive source
```python
stream_ready = asyncio.Event(); stream_done = asyncio.Event()
agent_stream_holder = []
async def _streaming_handler(req_ctx):
    async with model_request_stream(req_ctx.model, request_context=req_ctx, run_context=run_context) as sr:
        self._did_stream = True
        ctx.state.usage.requests += 1
        agent_stream = self._build_agent_stream(ctx, sr, req_ctx.model_request_parameters)
        agent_stream_holder.append(agent_stream)
        stream_ready.set()
        try:
            await stream_done.wait()
        finally:
            time_to_first_chunk_ctx.set(sr.time_to_first_chunk(request_start))
    return sr.get()
wrap_task = asyncio.create_task(ctx.deps.root_capability.wrap_model_request(
    run_context, request_context=wrap_request_context, handler=_streaming_handler))
ready_waiter = asyncio.create_task(stream_ready.wait())
try:
    await asyncio.wait({ready_waiter, wrap_task}, return_when=asyncio.FIRST_COMPLETED)
except BaseException:
    stream_done.set()                    # unblock handler before draining
    await cancel_and_drain(ready_waiter, wrap_task)
    raise
else:
    await cancel_and_drain(ready_waiter) # only the throwaway waiter is ours now
```

**Flow:** The `_streaming_handler` runs inside `wrap_model_request` (the capability middleware task). It opens the stream, sets `stream_ready`, and parks on `stream_done`. The node's `stream()` coroutine waits for `stream_ready` (or early task completion), yields the stream to the caller, then sets `stream_done` when the caller finishes. On the normal path, after the consumer finishes, the node awaits `wrap_task` for the final `ModelResponse`, handles `ModelRetry`/errors, and calls `_finish_handling`. On outer cancellation during the handoff wait, it sets `stream_done` (so a Temporal-absorbed CancelledError doesn't leave the handler parked) and drains both tasks before re-raising. On a consumer-side stream error, it cancels `wrap_task` and records the partial response in history (skipping the usage-limit check so it doesn't mask the real error).
**Invariant:** `wrap_task` is owned by the streaming lifecycle once the handoff succeeds; only the throwaway `ready_waiter` is cleaned up by the node. `stream_done` must be set on every path that could leave the handler parked. The event iterator is memoized and closed via `aclose_events()` so a consumer that breaks early doesn't leave the capability chain suspended.
**Probe:** `tests/test_streaming.py` and `tests/test_capability_stream_teardown.py` cover stream teardown and early-break cleanup.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "ModelRequestNode stream stream_ready stream_done wrap_task", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-event handoff (stream_ready/stream_done), the drain-on-cancel ordering, and the memoized+closed event iterator; adapt the event primitives to your async runtime (anyio/asyncio); omit nothing — the set-stream_done-on-cancel and drain-both-tasks invariants are portable. Coverage clean.
