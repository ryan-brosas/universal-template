<!-- capsule-v2 -->

# Service failure isolation — What dies when one item kills the worker: the item, the batch, or the singleton?

**Source:** prefect Apache-2.0 `main@ce79dd3d6cfa2b7337265498210dbc4d25bcdc98`; Codebase Memory `prefect`. **Question:** How does a shared background service survive bad items, and how do senders behave when the service itself dies?

## Exception = swallow and stay; BaseException = replace instance; death removes registry entry BEFORE logging

**Path/Symbol:** `src/prefect/_internal/concurrency/services.py:_run (158-181)`, `_main_loop (183-219)`, `QueueService.send (342-360)`; tests `tests/_internal/concurrency/test_services.py:108/:134/:498-563`.

**Signature:** `async def _run(self)` wraps `async with self._lifespan(): await self._main_loop()`.

**Data Shape:** per-item try/except `Exception`; service-level `except BaseException` around the whole run; traceback detail gated on `logger.isEnabledFor(logging.DEBUG)`.

### Decisive source
```python
async def _run(self) -> None:
    try:
        async with self._lifespan():
            await self._main_loop()
    except BaseException:
        self._remove_instance()
        # The logging call yields to another thread, so we must remove the
        # instance before reporting the failure to prevent retrieval of a
        # dead instance
        log_traceback = logger.isEnabledFor(logging.DEBUG)
        logger.error("Service %r failed with %s pending items.", ...)
```
```python
# _main_loop, per item:
try:
    await self._handle(item)
except Exception:
    log_traceback = logger.isEnabledFor(logging.DEBUG)
    logger.error("Service %r failed to process item %r", ...)
finally:
    self._queue.task_done()
```

**Flow:** item handler raising `Exception` → logged (message always; traceback only when internal logging level is DEBUG), queue marked done, loop continues — the SERVICE survives and keeps its identity. A `BaseException` (or `_lifespan`/loop crash) tears down the run: instance removed from the registry first, THEN error logged; subsequent `instance()` calls transparently construct a fresh replacement. Send into a stopped instance raises `RuntimeError("Cannot put items in a stopped service instance.")`.

**Invariant:** (1) Ordinary failures never kill telemetry: one poison item costs only itself (+its batch for BatchedQueueService). (2) Registry removal must precede the cross-thread log write — otherwise a concurrent sender could retrieve a dead singleton during the yield. (3) Traceback verbosity follows PREFECT_LOGGING_INTERNAL_LEVEL=DEBUG so user-facing noise stays at message-level by default.

**Probe:** direct tests `tests/_internal/concurrency/test_services.py:108 test_instance_returns_same_instance_after_error` (Exception ⇒ same singleton still usable), `:134 test_instance_returns_new_instance_after_base_exception` (BaseException ⇒ new instance serves item 2), `:498/:523/:546 test_*_contains_traceback_only_at_debug` parametrized DEBUG=True/INFO/WARNING=False ×3 planes.

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph '{"project": "prefect", "name_pattern": "^(EventsWorker|PrefectEventsClient|RETRYABLE_EXCEPTIONS)$", "limit": 6}'
```
(consumer-plane counterpart: events add their own retry ladder on top of this isolation)

## Verdict
Adopt the three-tier isolation policy (item-swallow / BaseException-replace / remove-before-log); adapt the debug-gating flag to your verbosity setting; omit Prefect-specific settings plumbing.
