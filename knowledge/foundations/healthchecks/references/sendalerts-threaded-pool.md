<!-- capsule-v2 -->
# sendalerts worker pool — a BoundedSemaphore that is also the work-discovery throttle

**Source:** healthchecks BSD-3-Clause `master@29b5ec25`; Codebase Memory `healthchecks`. **Question:** How does the notification worker overlap slow HTTP fan-out with new work, shut down on SIGTERM mid-flight, and why does every DB touch call close_old_connections()?

## Command.handle / process_one_flip / notify
**Path/Symbol:** `hc/api/management/commands/sendalerts.py:Command.__init__` (:61-65), `process_one_flip` (:91-121), `on_notify_done` (:81-89), `handle` (:184-216), module `notify` (:24-55).
**Signature:** `process_one_flip() -> bool`; `notify(flip: Flip) -> str | None` (runs in ThreadPoolExecutor); `handle(num_workers, pool, **options)`; `self.seats = BoundedSemaphore(num_workers)` sized in handle(), not __init__.
**Data Shape:** Loop contract: each phase method returns True = "more work may be pending, loop immediately", False = "idle or saturated, sleep 2s". Signal handler flips `self.shutdown`, never raises.

### Decisive source
```python
# hc/api/management/commands/sendalerts.py — seat BEFORE claim, release in callback
def process_one_flip(self) -> bool:
    if not self.seats.acquire(timeout=1):
        return False  # Workers busy, main thread should wait a bit
    flip = Flip.objects.filter(processed=None).first()
    if flip is None:
        self.seats.release()
        return False  # No work found
    q = Flip.objects.filter(id=flip.id, processed=None)
    num_updated = q.update(processed=now())
    if num_updated != 1:
        self.seats.release()
        return True   # another sendalerts process got there first
    statsd.incr("hc.sendalerts.processFlip")
    f = self.executor.submit(notify, flip)
    f.add_done_callback(self.on_notify_done)   # releases the seat EXACTLY once per future
    return True

# module-level notify() — thread-pool DB hygiene
if not connection.in_atomic_block:
    close_old_connections()   # threads reuse aged connections; tests skip via atomic block
```

**Flow:** handle() stamps the PG application_name ("sendalerts") for pg_stat visibility, warns the removed --pool flag, sizes seats+executor from --num-workers, installs SIGTERM/SIGINT handlers, then: drain handle_going_down → drain process_one_flip → sleep 2s unless shutdown. Shutdown is cooperative: loops check the flag between iterations, and `executor.shutdown(wait=True)` drains in-flight notifications before exit.
**Invariant:** The semaphore is acquired BEFORE the claim so a lost race cannot over-commit; the done-callback is the only releaser of submitted seats (release-once semantics; forgetting it deadlocks at num_workers claims). Every early-return path releases explicitly — porter must enumerate them. close_old_connections() belongs to BOTH the main loop pattern and the pool function because Django hands each pooled thread a possibly-dead connection; guarding on in_atomic_block keeps tests (which run inside transactions) deterministic. Per-channel outcomes stream into statsd counters `hc.notifications.<kind>.success|fail` plus dwell/sendTime gauges.
**Probe:** `hc/api/tests/test_sendalerts.py::test_it_processes_flip` (processed stamped, notify called once, statsd.incr called), `test_it_sets_next_nag_date` / `test_it_does_not_touch_already_set_next_nag_dates`, `test_it_increases_statsd_fail_counter` (TransportError side_effect → fail counter).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "healthchecks", query: "sendalerts executor seats notify close_old_connections", limit: 10 });
```
Resolves line-exact: process_one_flip :91-121, handle :184-216.

## Verdict
Adopt the seats-before-claim + callback-release pool shape, the boolean-return drain-loop control flow, cooperative signal shutdown, and per-thread connection refresh. Adapt worker count defaults and metrics names. Omit statsd if metric-less — but keep the success/fail split per channel kind, it is your delivery observability.
