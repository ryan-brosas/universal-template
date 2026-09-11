<!-- capsule-v2 -->
# Saga incremental summarization — dual watermarks with different clocks

**Source:** graphiti MIT `main@993e081a`; Codebase Memory `mnt-hdd-utopia-inspo-memory-graphiti`. **Question:** when a long-running story is summarized incrementally, which clock advances the "already summarized" cursor so backfilled episodes are never skipped?

## Saga dual-watermark summarization
**Path/Symbol:** `graphiti_core/graphiti.py`: `summarize_saga` (:438-568); filter-vs-temporal watermark narrative (:445-457); IoC-first fetch with raw-Cypher fallback (:483-523); summary clamp + monotone watermarks (:544-564).
**Signature:** `async summarize_saga(self, saga_id: str) -> SagaNode`; fetch cap `max_episodes = 200`; summary clamped to `MAX_SUMMARY_CHARS`.
**Data Shape:** saga carries `last_summarized_at` (wall-clock ingestion cursor) and `last_summarized_episode_valid_at` (event-time cursor, max valid_at covered by current summary).

### Decisive source
```python
# Filter watermark = WALL CLOCK. created_at is monotonic with processing time,
# so an episode BACKFILLED today with valid_at in the past is still picked up:
if since is not None:
    ... WHERE e.created_at > $since
        ORDER BY e.valid_at ASC, e.created_at ASC LIMIT $limit
else:
    # First-run branch has no `since` to push down: take newest N DESC then
    # REVERSE in Python for chronological prompt order:
    ORDER BY e.valid_at DESC, e.created_at DESC LIMIT $limit
    records = list(reversed(records))

# Temporal watermark advances ONLY forward — never regresses on a batch
# whose episodes carry no valid_at:
saga.last_summarized_at = utc_now()
if valid_ats:
    new_episode_watermark = max(valid_ats)
    if (saga.last_summarized_episode_valid_at is None
            or new_episode_watermark > saga.last_summarized_episode_valid_at):
        saga.last_summarized_episode_valid_at = new_episode_watermark
```

**Flow:** load saga → `since = last_summarized_at` → try driver's graph-operations interface (`_saga_get_episode_contents`), fall back to dialect Cypher (`HAS_EPISODE` traversal; existing summary passed as LLM context so nothing is lost) → empty batch ⇒ log-and-return unchanged → one `summarize_sagas.summarize_saga` prompt over episode contents → clamp summary → set wall-clock watermark unconditionally, event-time watermark only if strictly greater → save.
**Invariant:** (1) the two watermarks are NOT interchangeable: consumers asking "how recent is the summary CONTENT in event time" must read `last_summarized_episode_valid_at`; using it as the fetch filter would skip backfilled episodes forever; (2) event-time watermark is write-once-monotone per run (None-or-greater), wall-clock watermark always advances after a successful summary; (3) fallback Cypher keeps chronological order via DESC+reverse because `since` can't be bound on first run.
**Probe:** anchored at repo root. Battery: `grep -c 'saga.last_summarized_episode_valid_at is None' graphiti_core/graphiti.py` → 1; `grep -c 'ORDER BY e.valid_at DESC, e.created_at DESC' graphiti_core/graphiti.py` → 2; `grep -c 'records = list(reversed(records))' graphiti_core/graphiti.py` → 1; `grep -c 'summary\[:MAX_SUMMARY_CHARS\]' graphiti_core/graphiti.py` → 1; `grep -c 'max_episodes = 200' graphiti_core/graphiti.py` → 1. Direct-test coverage caveat: no core unit suite executes `summarize_saga` at this pin (grep of tests/ finds no saga test); behavior pinned indirectly by `mcp_server/tests/test_core_parity.py::test_core_exposes_parity_methods :251-261` (method-existence guard incl. pre-0.29 cores) — treat semantics as source-verified only.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-memory-graphiti", query: "summarize_saga last_summarized_at HAS_EPISODE watermark", limit: 5, fields: ["signature", "name", "file"] });
// rank-1: Graphiti.summarize_saga :438-568
```

## Verdict
Adopt the dual-watermark split (wall-clock filter / event-time consumer field) and the monotone advance rule for any incremental roll-up over timestamped records; adapt the fetch window and prompt; omit saga persistence details for hosts without node-typed summaries. Coverage caveat stated above.
