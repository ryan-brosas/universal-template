<!-- capsule-v2 -->

# Queue-service singleton on a shared global loop — How do you expose one background batch service per config key from any thread?

**Source:** prefect Apache-2.0 `main@ce79dd3d6cfa2b7337265498210dbc4d25bcdc98`; Codebase Memory `prefect`. **Question:** How does Prefect guarantee a single queue-service instance per argument set, started from any thread, while its async loop always runs on ONE process-wide event loop?

## Singleton registry + global-loop-thread binding

**Path/Symbol:** `src/prefect/_internal/concurrency/services.py:_QueueServiceBase.instance (306-318)`, `_new_instance (323-338)`, `start (100-114)`, fork reset `:28-54`, `reset_for_fork (84-98)`.

**Signature:** `instance(cls, *args: Hashable) -> Self`; `start(self) -> None`; `_new_instance(cls, *args) -> Self`.

**Data Shape:** Class-level `_instances: dict[int, Self]` guarded by a class `threading.Lock`; instance key = `hash((cls, *args))`; `_active_services: WeakSet` tracks live instances for the fork handler.

### Decisive source
```python
def start(self) -> None:
    loop_thread = get_global_loop()
    if not asyncio.get_running_loop() == getattr(loop_thread, "_loop"):
        raise RuntimeError("Services must run on the global loop thread.")
    self._loop = asyncio.get_running_loop()
    ...
    self._queue_get_thread.start()
    self._started = True

@classmethod
def _new_instance(cls, *args: Hashable) -> Self:
    instance = cls(*args)
    # If already on the global loop, just start it here to avoid deadlock
    if threading.get_ident() == get_global_loop().thread.ident:
        instance.start()
    else:
        from_sync.call_soon_in_loop_thread(create_call(instance.start)).result()
    return instance

os.register_at_fork(after_in_child=_reset_services_after_fork)
```

**Flow:** caller thread → `instance(*args)` → lock; key miss ⇒ `_new_instance` constructs and starts: on the global-loop thread it starts inline; any other thread blocks on `call_soon_in_loop_thread(start).result()` so the service's asyncio task is born on the shared global loop. Key hit returns the live instance. After `fork()` in the child, every tracked service is marked stopped with a fresh queue/lock and the class registry is cleared, so a child never signals a parent's dead threads.

**Invariant:** (1) Exactly one live instance per `(class, args)` — senders can never split work across duplicates of the same config. (2) The service task ALWAYS runs on the process-global event loop, never the caller's loop; starting from a foreign loop would bind drain/stop semantics to a loop someone else may close. (3) A fork() child must consider all inherited services dead — resetting state beats trying to resurrect threads that were never copied.

**Probe:** direct tests `tests/_internal/concurrency/test_services.py:80 test_instance_returns_same_instance`, `:93 test_instance_returns_new_instance_with_unique_key`, `:100 test_different_subclasses_have_unique_instances`, `:85 test_instance_returns_new_instance_after_stopping`; bounded-queue fork contract `tests/events/client/test_bounded_queue.py:75 test_reset_for_fork_preserves_maxsize`.

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph '{"project": "prefect", "name_pattern": "^(_QueueServiceBase|QueueService|BatchedQueueService|FutureQueueService)$", "limit": 8}'
```
(observed rank-1..4 = the four kernel classes in `src/prefect/_internal/concurrency/services.py`, lines 57-539)

## Verdict
Adopt singleton-per-config-key registry + dedicated global loop thread + at-fork reset for any in-process telemetry shipper; adapt the global-loop mechanism to your host's loop management; omit Prefect's WorkerThread plumbing details.
