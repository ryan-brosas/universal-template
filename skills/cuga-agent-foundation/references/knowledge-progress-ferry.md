<!-- capsule-v2 -->
# Thread-to-loop progress ferry — how do worker-thread callbacks report progress without corrupting task status, and why must you drain before writing "completed"?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** An embedder runs in `asyncio.to_thread` and wants to emit progress into an asyncio-owned metadata store — what's the race, and what ordering makes the final status write win?

## run_coroutine_threadsafe + tracked futures + drain-before-completion
**Path/Symbol:** `src/cuga/backend/knowledge/engine.py:2495-2521` (`_emit_progress`, `progress_cb`), drain loop `:2638-2654`; adapter-side contract pinned by `tests/unit/test_knowledge_progress.py`.
**Signature:** `progress_cb(stage: str, done: int, total: int) -> None` (sync, called from worker thread); `_emit_progress(stage, done, total) -> Awaitable` executed on the captured outer loop.
**Data Shape:** Emits are partial task updates `{filename, stage, progress:{done,total}}` — deliberately WITHOUT a `status` key; futures accumulate in `progress_futures: list[concurrent.futures.Future]`.

### Decisive source
```python
# engine.py:2639-2651 — the drain, with the blocking-call trap called out
# Drain any in-flight progress emits before the completion update so a
# late write cannot overwrite ``status="completed"`` back to ``"processing"``.
# Use ``asyncio.wait_for`` over a wrapped concurrent Future so the drain
# stays on the event loop — ``fut.result(timeout=...)`` is a blocking call
# that would stall the asyncio thread for up to len(progress_futures) *
# timeout (~20s for 10 emits). Per Sami's review (Dec 2026) — actual
# production block.
for fut in progress_futures:
    try:
        await asyncio.wait_for(asyncio.wrap_future(fut), timeout=2.0)
    except (asyncio.TimeoutError, Exception):
        pass
```
Three invariants stack here. (1) **Status-field omission**: because emits never carry `status`, even a stray late write that races the completion update can only touch `stage`/`progress` keys — it cannot un-flip `status="completed"` (comment at `:2474-2479`; adapter contract pinned by test). (2) **Drain-before-completion**: every tracked future is awaited BEFORE `update_task(status="completed")`, so no emit lands after completion at all. (3) **Loop-safe waiting**: `asyncio.wrap_future` + `wait_for`, never `concurrent.Future.result(timeout=)` which would block the event-loop thread.

**Flow:** capture `outer_loop = asyncio.get_running_loop()` (`:2500`) → define thread-safe `progress_cb` that ferries each emit via `asyncio.run_coroutine_threadsafe(_emit_progress(...), outer_loop)` and appends the returned future to the list → hand `progress_cb` to the vector adapter's insert → on return, drain all futures with 2s per-future timeout, swallowing failures (progress is best-effort) → write final status.
**Invariant:** The completion status write must be the LAST writer for the `status` field: achieved by (a) emits structurally lacking `status` and (b) draining all queued emits first. Per-future timeouts keep a hung metadata store from stalling ingest.

**Probe:** `tests/unit/test_knowledge_progress.py:50+` — adapter-level pins: callback invoked once per embed sub-batch with monotonic counts, and payload NEVER contains `status`. Engine-side drain itself has no dedicated unit test (module docstring says it needs full-ingest fixtures); coverage caveat recorded — read source when porting.
