<!-- capsule-v2 -->
# SourceLedger — content-identity cite_ids that survive multi-hop retrieval and restarts, scoped to the current turn

**Source:** cuga-agent Apache-2.0 `main@5de53ade`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** How do you give every retrieved chunk a stable citation id that survives later hops, turns, and even process restarts — while guaranteeing an answer can never cite evidence not retrieved in THIS turn?

## Thread-scoped ledger + turn scoping
**Path/Symbol:** `src/cuga/backend/knowledge/sources.py` (`SourceLedger` :72-203; `register` :95-127; `_content_key` :66-69; `begin_turn` :129-137; `_evict_if_needed` :190-203; `restore` :153-188; thread registry `get_ledger`/`begin_ledger_turn`/`drop_ledger` :208-255).
**Signature:** `register(result, *, query: str) -> str` (returns `"s<N>"`); `get(cite_id) -> SourceRecord | None`; `mark_cited(cite_id)`; `retrieved_this_turn(cite_id) -> bool`; `restore(snapshot: dict) -> None`.
**Data Shape:** identity key = sha1-16 of `(scope|filename|page|sha1-16(text))` → same chunk text from any hop/turn maps to the SAME id; page/filename differences make DIFFERENT sources. Records carry self-contained snapshot fields (`to_snapshot(n)` renders without ledger/collection/doc existing). Registry: per-thread ledgers in an LRU capped at 300 threads.

### Decisive source
```python
# :104-110 — re-hit refreshes recency AND re-admits to current-turn scope
existing = self._by_key.get(key)
if existing is not None:
    self._by_key.move_to_end(key)
    # Re-retrieving this turn makes it current-turn evidence again.
    self._turn_ids.add(existing.cite_id)
    return existing.cite_id

# :167-172 — restore bumps counter EVEN on duplicate keys (fix 1 regression)
self._counter = max(self._counter, int(m.group(1)))
if key in self._by_key or cite_id in self._by_cite_id:
    return

# :190-201 — eviction prefers oldest UNCITED; all-cited falls back to absolute oldest
```

**Flow:** every retrieval registers its chunks under the thread's lock (retrieval runs on worker threads, resolution on the event loop) → `begin_turn()` clears ONLY the turn-id set at genuine NEW-user-turn boundaries (server event_stream / SDK invoke); HITL resumes deliberately do NOT call it, so post-resolve answers keep their pre-interrupt citations → restore() rehydrates persisted snapshots with original ids and pushes the counter past them so new ids never collide with ids already printed in the on-disk conversation.
**Invariant:** A cite_id resolves only if registered during the CURRENT turn (stale ids strip exactly like hallucinated ones — this is the mis-attribution regression: an AppWorld chunk cited for a scholarship answer); re-retrieval legitimately re-admits. Eviction must never drop cited records while uncited exist (cited ids are referenced by persisted message history). Restore-before-begin_turn ordering means rehydrated ids stay OUT of turn scope until actually re-retrieved.
**Probe:** direct tests `tests/unit/test_source_ledger.py::test_register_is_idempotent_for_same_content` (:36), `::test_cap_evicts_oldest_uncited_first` (:57), `::test_re_retrieval_refreshes_recency_before_eviction` (:69), `::test_restore_then_register_continues_numbering` (:113), `::test_restore_duplicate_is_noop_but_still_bumps_counter` (:123), `tests/unit/test_citation_resolver.py::test_marker_from_earlier_turn_is_stripped` (:193), `::test_chunk_re_retrieved_this_turn_resolves` (:226), `::test_begin_ledger_turn_is_noop_without_ledger` (:304).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "SourceLedger register _content_key begin_turn restore get_ledger", limit: 10 });
```

## Verdict
Adopt content-hash identity + monotone sN counters + explicit turn-scope sets cleared only at real turn boundaries, write-through snapshots with counter-bump-on-duplicate restore, and cited-first eviction. Adapt cap sizes (500 records/300 threads) and snapshot schema to your store. Omit nothing from turn scoping — dropping it reintroduces cross-turn mis-attribution, which is worse than no citation.
