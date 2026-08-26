<!-- capsule-v2 -->
# Ticket-ledger write path — how do you count usage per user so quota gates and purchased-ticket spending stay consistent?

**Source:** sweep (Apache-2.0) `main@a8b8b67bda4f`; Codebase Memory `sweep`. **Question:** When a ticket completes, what exact MongoDB writes record it, and how are over-cap tickets converted into purchased-ticket spend in one atomic-ish step?

## ChatLogger._add_successful_ticket: month+date $inc upsert with same-write purchase decrement
**Path/Symbol:** `sweepai/utils/chat_logger.py:_add_successful_ticket` (:83–109); fire-and-forget wrapper `add_successful_ticket` (:111–114).
**Signature:** `_add_successful_ticket(self, gpt3=False)`; `add_successful_ticket(self, gpt3=False) -> None` (spawns `Thread` appended to `global_threads`).
**Data Shape:** `self.data` dict carries `username`/`assignee`; counters live on a per-username document with dynamic field names — `current_month = "%m/%Y"`, `current_date = "%m/%Y/%d"` (both computed at construction). Class-level mutable dicts `_ticket_count_cache` / `_user_field_cache` are shared across ALL ChatLogger instances in the process.

### Decisive source
```python
username = self.data.get("assignee", self.data["username"])
update_fields = {self.current_month: 1, self.current_date: 1}
if gpt3:
    key = f"{self.current_month}_gpt3"
    update_fields = {key: 1}
self.ticket_collection.update_one(
    {"username": username}, {"$inc": update_fields}, upsert=True
)
ticket_count = self.get_ticket_count()
should_decrement = (self.is_paying_user() and ticket_count >= 500) or (
    self.is_consumer_tier() and ticket_count >= 20
)
if should_decrement:
    self.ticket_collection.update_one(
        {"username": username}, {"$inc": {"purchased_tickets": -1}}, upsert=True
    )
```

**Flow:** ticket success → background thread `$inc`s BOTH month and date counters in one upsert (or only `{month}_gpt3` for degraded-tier tickets) → re-reads count through the class-level cache → if now ≥ cap for the tier, immediately `$inc`s `purchased_tickets: -1` → all Mongo I/O is off-thread so the request path never blocks; threads are parked in `global_threads` for later `PyThreadState_SetAsyncExc` teardown (see latest-wins capsule).
**Invariant:** The increment and the purchase-spend are two separate updates, not one transaction — a crash between them double-counts or under-spends, accepted by design. `gpt3=True` writes ONLY the gpt3 bucket, so degraded-tier runs never consume the normal monthly counter. Reads after this write hit `_ticket_count_cache`, which is never invalidated per instance — staleness within a process is tolerated because every writer goes through the same class-level cache.
**Probe:** No offline unit test exists (MongoDB-dependent module; graph TESTS-edge query returned zero rows both directions — coverage caveat). Deterministic probe: `grep -c 'upsert=True' sweepai/utils/chat_logger.py` → 2 at pin; `grep -c '_gpt3' sweepai/utils/chat_logger.py` → 4.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "sweep", query: "ChatLogger successful ticket count quota paying user", limit: 10, fields: ["signature", "lines"] });
// executed at pin: ChatLogger.use_faster_model :172-186, get_ticket_count :119-142,
// _get_user_field :144-160, _add_successful_ticket :83-109, add_successful_ticket :111-114
```

## Verdict
Adopt the dual-granularity counter (month + day fields on one document, `$inc` with upsert), the same-pass purchase decrement when the fresh count crosses cap, and off-thread ledger writes collected in a global registry. Adapt field-name formats and tier thresholds to your billing model; replace the unbounded class-level dicts with an LRU/TTL cache if your process is long-lived. Omit Sweep's gpt3 special-case unless you also degrade model tiers.
