<!-- capsule-v2 -->
# Thread-safe control-plane submission — How do pause/stop/skip reach a supervisor running on a different thread's event loop?

**Source:** CAMEL-AI/camel Apache-2.0 `master@13dc7a7d`; Codebase Memory `ext-camel`. **Question:** What is the dispatch rule that makes control methods safe before, during, and after the workforce loop exists?

## Dual-path submit + flag fallbacks for the loopless window
**Path/Symbol:** `camel/societies/workforce/workforce.py:Workforce._submit_coro_to_loop` (:5804-5819), `pause` (:2040-2060), `stop_gracefully` (:2098-2119), `skip_gracefully` (:2219-2241).
**Signature:** `def _submit_coro_to_loop(self, coro: Coroutine) -> None`; public controls are sync methods.
**Data Shape:** `_loop: Optional[asyncio.AbstractEventLoop]`, `_pause_event: asyncio.Event` (SET = not paused; cleared by pause), boolean flags `_stop_requested/_skip_requested`.

### Decisive source
```python
loop = self._loop
if loop is None or loop.is_closed():
    logger.warning("Cannot submit coroutine - no active event loop"); return
try: running_loop = asyncio.get_running_loop()
except RuntimeError: running_loop = None
if running_loop is loop:
    loop.create_task(coro)
else:
    asyncio.run_coroutine_threadsafe(coro, loop)
```

**Flow:** every control method branches on `self._loop and not self._loop.is_closed()`: live loop → submit the async variant through `_submit_coro_to_loop`; NO loop → apply the same effect synchronously to plain fields (pause: state→PAUSED + clear event only if RUNNING; stop_gracefully: set `_stop_requested` AND `self._pause_event.set()` so a later-started loop can't wake up paused-and-stopped and deadlock; skip: same event release). `stop_immediately` (:2121-2169) additionally drains pending tasks, removes in-flight packets from the channel (`get_in_flight_tasks` → `remove_task`) resetting the counter to 0 EVEN IF channel cleanup fails, cancels child listeners, and flips state STOPPED. The in-flight decrement helper itself is guarded (`if self._in_flight_tasks > 0`, :1512) so double-decrements clamp at zero.
**Invariant:** Control flags are PLAIN BOOLEANS written cross-thread — safety comes from the loop-side polling order (pause gate → stop gate → skip gate), never from locks; any port must keep the "release pause event when stopping" pairing or the loop sleeps forever on a cleared Event.
**Probe:** `grep -c '_pause_event.set()' camel/societies/workforce/workforce.py` → 13 (init not-paused + resume/stop/skip/loopless paths); `grep -c 'run_coroutine_threadsafe' camel/societies/workforce/workforce.py` → 4 (helper :5819 plus child-workforce starts :3014/:3020/:3244).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-camel", query: "_submit_coro_to_loop run_coroutine_threadsafe pause stop_requested", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt dual-path (coroutine-submit vs flag-fallback) lifecycle control plus stop-releases-pause. Adapt which flags you poll. Omit snapshot/restore machinery unless you need human-in-the-loop time travel.
