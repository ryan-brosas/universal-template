<!-- capsule-v2 -->

# BatchedQueueService flush window — When does a batch ship: size budget, time window, or both?

**Source:** prefect Apache-2.0 `main@ce79dd3d6cfa2b7337265498210dbc4d25bcdc98`; Codebase Memory `prefect`. **Question:** How does a batching worker flush promptly at low throughput while still capping batch size at high throughput?

## Pull with a per-window timeout; queue.Empty closes the batch

**Path/Symbol:** `src/prefect/_internal/concurrency/services.py:BatchedQueueService (452-539)` — `_main_loop (471-521)`, `_handle_batch (523-527)`, `_get_size (534-539)`, class knobs `_max_batch_size/_min_interval (460-461)`; deadline helpers `src/prefect/_internal/concurrency/cancellation.py:get_deadline/get_timeout (486-507)`.

**Signature:** `_max_batch_size: int` (class attr); `_min_interval: Optional[float] = None`; `async def _handle_batch(self, items: list[T]) -> None`.

**Data Shape:** batch accumulates until cumulative `_get_size(item)` reaches `max_batch_size`; the get-block carries the REMAINING window as its timeout.

### Decisive source
```python
async def _main_loop(self):
    done = False
    while not done:
        batch: list[T] = []
        batch_size = 0
        deadline = get_deadline(self.min_interval)
        while batch_size < self.max_batch_size:
            try:
                item = await self._queue_get_thread.submit(
                    create_call(self._queue.get, timeout=get_timeout(deadline))
                ).aresult()
                if item is None:
                    done = True; break
                batch.append(item)
                batch_size += self._get_size(item)
            except queue.Empty:
                # Process the batch after `min_interval` even if it is smaller
                break
        if not batch:
            continue
        try:
            await self._handle_batch(batch)
        except Exception:
            ... logger.error("... failed to process batch of size %s", ...)
```

**Flow:** each cycle computes a fresh deadline from `min_interval`; items are pulled one-by-one with the remaining window as the block timeout; hitting max size, window expiry (`queue.Empty`), or the stop sentinel ends collection; an empty collection restarts the loop; a collected batch ships even on failure — the exception is logged and SWALLOWED, so failed batches are dropped, never requeued. With `_min_interval=None`, `get_timeout` returns None ⇒ blocking get ⇒ flush happens only when the batch fills or stop arrives.

**Invariant:** (1) Batch size can be measured in arbitrary units via `_get_size` (APILogWorker uses payload BYTES, popping a private per-item size key). (2) The timeout applies PER GET, not per cycle, so a steady trickle never starves past one interval after arrival. (3) Batch handling is fire-and-forget: no retry/no requeue — porters needing delivery guarantees must build them in the client (see events-websocket-resend-checkpoint).

**Probe:** direct tests `tests/_internal/concurrency/test_services.py:402 test_batched_queue_service` (max=2 → calls [1,2],[3,4],[5]), `:415 test_batched_queue_service_min_interval` (interval 0.01 flushes singletons), `:523 test_batched_queue_service_item_failure_contains_traceback_only_at_debug`.

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph '{"project": "prefect", "name_pattern": "^BatchedQueueService$", "limit": 4}'
```
(observed rank-1: `BatchedQueueService Class src/prefect/_internal/concurrency/services.py 452-539`)

## Verdict
Adopt size-or-time batch windows with per-get remaining-timeouts and unit-customizable sizing; adapt units and intervals to your transport; omit the WorkerThread submit indirection if your loop blocks safely.
