<!-- capsule-v2 -->
# Cumulative stream-events store — how does one row per thread survive multi-turn appends, corrupt rows, and Try-It-Out garbage?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-cuga-agent`. **Question:** How do I persist per-turn UI event streams so replays stay complete without letting one bad row or abandoned threads poison the store?

## ConversationHistoryDB: append+resequence, corruption tolerance, NOT-EXISTS GC
**Path/Symbol:** `src/cuga/backend/server/conversation_history.py:ConversationHistoryDB.save_stream_events` (370–418), `.gc_ephemeral_stream_events` (449–480), `get_conversation_db` (511–515) singleton.
**Signature:** `async def save_stream_events(agent_id, thread_id, user_id, events: List[Dict]) -> bool`; `async def gc_ephemeral_stream_events(older_than_days: int = 7) -> int`.
**Data Shape:** table `stream_events(tenant_id, instance_id, agent_id, thread_id, user_id, events JSON, created_at, updated_at)` — ONE cumulative row keyed by the 5-tuple; each event `{event_name, event_data, timestamp, sequence}`.

### Decisive source
```python
raw_existing = json.loads(existing["events"]) if existing["events"] else []
if not isinstance(raw_existing, list): raw_existing = []            # corrupt payload ⇒ start clean
existing_events = [e for e in raw_existing if isinstance(e, dict)]  # drop non-dict entries
max_seq = max((e.get("sequence", -1) for e in existing_events), default=-1)
renumbered = [{**e, "sequence": max_seq + 1 + offset} for offset, e in enumerate(events)]
events_json = json.dumps(existing_events + renumbered)
...
removed = getattr(store, "_last_rowcount", 0) or 0   # portable rowcount: no SELECT changes() / pg dialect split
```

**Flow:** caller buffers only THIS turn's events (server kernel capsule) → save reads the existing row, tolerates non-list payloads and non-dict entries by dropping them, renumbers new events from max existing sequence, writes the merged list back → GC (startup, lifespan) deletes rows updated >7d ago that have NO sibling conversation_history row (NOT EXISTS over the same 5-tuple) — exactly the Try-It-Out/X-Disable-History threads whose events_only saves would otherwise accumulate forever. All failures log-and-return False/0; never raise into the stream path.
**Invariant:** sequences stay unique and monotonic across the MERGED list even when a prior row was partially corrupt; GC must key on the full tenant/instance scoping tuple so multi-tenant rows can't delete each other; persistence failure must never break the user-visible run.
**Probe:** `tests/unit/test_conversation_history_stream_events.py` (`test_save_stream_events_appends_and_resequences`, tolerance tests) and `tests/unit/test_ephemeral_stream_events.py` — executed this run: pass.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-cuga-agent", query: "save_stream_events gc_ephemeral resequence conversation history", limit: 8 });
```

## Verdict
Adopt single-cumulative-row append with max-seq renumbering, corrupt-entry dropping, and the NOT-EXISTS GC with portable rowcount. Adapt the scoping tuple to your tenancy model; omit the conversation sidebar projection (first_message preview) unless you render threads.
