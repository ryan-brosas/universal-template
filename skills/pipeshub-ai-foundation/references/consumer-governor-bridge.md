<!-- capsule-v2 -->
|# Worker-loop→main-loop concurrency bridge + governor-backed admission — how do Kafka/Redis consumer worker threads share Redis leases, retry ledgers and a ResourceGovernor with the main loop safely?

**Source:** pipeshub-ai Apache-2.0 `main@c28d133…`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-pipeshub-ai`. **Question:** When message processing runs on per-thread event loops but the distributed primitives (Redis lease manager, retry manager) are only safe on the main loop — and a node-local adaptive gate now sits in front of parsing — what is the exact bridge/admission/release choreography?

## Host-protocol functions over a shared instance; ParsingAdmission carries its own release closure
**Path/Symbol:** `backend/python/app/services/messaging/consumer_concurrency.py` (whole file, L1–482); consumers wired in `services/messaging/{kafka/consumer/indexing_consumer.py,redis_streams/indexing_consumer.py}`; direct tests `tests/unit/services/messaging/test_consumer_concurrency_governor.py` (270L).
**Signature:** module-level functions taking `host` first: `bridge_to_main_loop(host, coro, timeout=5.0)`, `acquire_distributed_slot(host, pool, owner, limit, deadline_seconds=None) -> bool`, `renew_distributed_slots(host, leases)` (raises), `index_ceiling/parse_ceiling(host, tier)`, `pending_task_ceiling(host)`, `acquire_parsing_slot(host, tier, size_bytes) -> ParsingAdmission`, `release_parsing_slot(admission|None)`, `report_memory_incident_if_applicable(host, message_id, error)`.
**Data Shape:** `ConcurrencyHost` Protocol = structural contract over existing attributes (`main_loop`, `governor`, `parsing_semaphore`, `concurrency_manager`, `retry_manager`, `_gate_waiters`, `_futures_lock`); `ParsingAdmission(cost, _release: Callable[[],None])`; `GateWaiterToken` (`__slots__`, `_admitted/_released` latch pair).

### Decisive source
```python
# Bridge: every cross-thread call is run_coroutine_threadsafe + wrap_future
# + wait_for(timeout) + cancel-on-anything; coro.close() before raising so
# "coroutine never awaited" warnings can't fire on the failure paths.
future = asyncio.run_coroutine_threadsafe(coro, main_loop)
try:    return await asyncio.wait_for(asyncio.wrap_future(future), timeout)
except BaseException:
        future.cancel(); raise

# Admission returns WHAT to release, not a primitive type to branch on:
async def acquire_parsing_slot(host, tier, size_bytes):
    if host.governor is not None:
        resolved_tier = tier if tier is not None else ParseTier.HEAVY
        cost = parse_cost(resolved_tier, size_bytes)
        gate = host.governor.gate(gate_pool(resolved_tier))
        await gate.acquire(cost=cost)
        return ParsingAdmission(cost=cost, _release=lambda: gate.release(cost))
    sem = host.parsing_semaphore            # legacy fallback, cost always 1
    await sem.acquire()
    return ParsingAdmission(cost=1, _release=sem.release)

def release_parsing_slot(admission):        # None-safe for bare finally:
    if admission is None: return
    admission._release()

# Cluster lease sized to the CEILING (never the live adaptive value):
def index_ceiling(host):
    return host.governor.ceilings.index if host.governor \
        else messaging_env.max_concurrent_indexing
```

**Flow:** consumer worker thread spawns a task → `GateWaiterToken` increments `_gate_waiters` at spawn (backpressure counts tasks waiting for LOCAL admission: retry-backoff, distributed-lease wait, or the gate itself) → `pending_task_ceiling()` pauses partition/stream reads when waiters exceed `max(index,heavy ceilings)×4` (explicit `MAX_PENDING_INDEXING_TASKS` env wins) → distributed lease acquired via bridged `try_acquire` polling (per-record pool carries a DEADLINE so duplicate deliveries of one record can't convoy the pipeline while holding the outer slot; the indexing pool has none — contended only by genuinely different records) → `acquire_parsing_slot` routes tier+cost through the governor (or legacy semaphore) → renewal loop re-arms every lease each `interval ≤ lease_seconds/3` and RAISES when a lease can't be renewed before its safety deadline (processing must cancel rather than keep a slot the fleet reassigned).
**Invariant:** (1) The distributed Redis lease stays sized to the RESOLVED CEILING, never the live adaptive value — cluster cap vs node-local cap are different numbers by design (:74/:109 tests pin ceiling-readings under shrink). (2) Light parse gets its OWN lease pool name (`parsing:light`) and its own ceiling — a Jira parse must never consume a Docling-sized heavy lease. (3) Functions read/write host ATTRIBUTES instead of a base class deliberately, so tests patching (name-mangled) methods keep working — porters who "clean this up" into inheritance break both consumers' test suites. (4) `_normalize_operation` collapses `op:record:<id>` to `op:record` or the throttle-log map grows one entry PER RECORD forever. (5) Renewal raise-vs-return split: losing a lease must cancel processing (fail loud), while transient renew errors only log-throttle (30s per normalized op). (6) `MemoryError` feeds `report_memory_incident` unconditionally when a governor exists — cgroup OOM usually SIGKILLs instead, so this catchable path is a cheap backstop.
**Probe:** `tests/unit/services/messaging/test_consumer_concurrency_governor.py` :37–270 — env-fallback vs resolved-ceiling :42, light-split-from-heavy :50, explicit-cap-caps-both-tiers :65, ceiling-unaffected-by-adaptive-shrink :74, waiter-count-from-construction-until-admit :127, release-after-admit-no-op :134, admitted-tasks-don't-block-new-waiters :151, legacy-semaphore-cost-one :177, missing-semaphore raises :189, heavy/light tier→gate routing :195/:208.
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph --project mnt-hdd-utopia-inspo-platforms-pipeshub-ai --query "acquire_parsing_slot GateWaiterToken pending_task_ceiling" --detail ids
```

## Verdict
Adopt: the host-protocol function-module shape for cross-cutting consumer plumbing, the bridge trio (run_coroutine_threadsafe + wrap_future + bounded wait + future.cancel), ceiling-not-live-value distributed sizing, deadline-differentiated lease pools, the ParsingAdmission carry-your-release pattern, and the waiter-token backpressure counter. Adapt pool names/env keys. Omit nothing material — routing/backpressure/waiter branches all test-pinned upstream; bridge timeout/renewal-deadline values are config-driven.
