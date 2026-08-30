<!-- capsule-v2 -->
# SnapshotHistorySource: snapshot-union recovery of pre-compaction originals

## Source / Question
`pydantic_ai_harness/conversation_search/_source.py` — How do you recover the ORIGINAL message record of a run when the persistence substrate stores per-boundary full-history snapshots and compaction strategies persist their edits forward (so the latest snapshot is post-compaction)? Porters index only the newest snapshot and silently lose everything compaction replaced.

## Path / Symbol
`conversation_search/_source.py` — `HistorySource` protocol (:51–71), `SnapshotStore` narrow read protocol (:74–92), `message_hash` (:95–104), `_overlap_length` (:107–112), `is_summary_artifact` (:115–119), `SUMMARY_PREFIX` (:35–48), `SnapshotHistorySource.run_history` (:156–166), constructor guard (:138–150).

## Signature
```python
async def run_history(self, *, run_id: str) -> list[ModelMessage]:
    history: list[ModelMessage] = []
    history_hashes: list[str] = []
    for snapshot in await self._store.list_snapshots(run_id=run_id):
        messages = [m for m in snapshot.messages if not is_summary_artifact(m)]
        snapshot_hashes = [message_hash(m) for m in messages]
        overlap = _overlap_length(history_hashes, snapshot_hashes)
        history.extend(messages[overlap:])
        history_hashes.extend(snapshot_hashes[overlap:])
    return history
```

## Data Shape
Input: snapshots in write order, each holding the full live history at one step boundary. Output: one durable record per run — originals plus everything compaction never touched, summary artifacts excluded. `HistorySource.list_runs()` returns runs sorted by `started_at` ascending; unknown `run_id` yields `[]`.

### Decisive source
1. **Suffix/prefix overlap reconciliation** (`_overlap_length` :107–112): longest suffix of accumulated history matching a prefix of the snapshot — "the overlap is reconciled by sequence position, so byte-identical messages at distinct positions remain in the record."
2. **Content-hash dedup, not identity** (`message_hash` :95–104): sha256 over `ModelMessagesTypeAdapter.dump_json([message])` — durable executors (Temporal/DBOS) re-instantiate messages between steps, so object-identity dedup would re-append duplicates.
3. **Byte-exact summary marker** (`SUMMARY_PREFIX` :35–48): `'Summary of previous conversation:\n\n'` mirrors compaction's own literal INCLUDING the blank line — that blank line is what keeps a user-authored prompt merely opening with the same sentence inside the corpus. Kept as a local literal to avoid coupling to compaction internals.
4. **Complete-only default** (:133–135): shipped stores' `list_snapshots` defaults to `complete` snapshots, so `interrupted` captures (unsettled tool work, synthesized tool returns) stay out of the corpus.
5. **Construction-time seam check** (:138–150): `isinstance(store, SnapshotStore)` fails loud at construction because `list_snapshots` is not yet on the `StepStore` protocol — a third-party store can satisfy `StepStore` without it and would otherwise surface as an obscure AttributeError deep inside a tool call.

## Flow / Invariant
Enumerate snapshots oldest→newest → strip summary artifacts → hash → drop the reconciled prefix overlap → extend. Invariants: never re-append a byte-identical message already recorded; never index a derived compaction summary; identical content at distinct sequence positions survives; the search layer persists nothing itself.

## Probe (direct test)
`tests/conversation_search/test_conversation_search.py::TestSnapshotHistorySource`: `test_union_recovers_precompaction_originals` (:133), `test_repeated_identical_messages_keep_distinct_positions` (:146), `test_summary_skip_stays_in_sync_with_compaction` (:155), `test_user_authored_summary_lookalike_stays_in_the_corpus` (:172), `test_interrupted_snapshots_stay_out_of_the_corpus` (:186), `test_rejects_store_without_snapshot_seam` (:236).

## Retrieve
`search_graph --project pydantic-ai-harness --query 'SnapshotHistorySource run_history _overlap_length SUMMARY_PREFIX'`

## Verdict
**Adopt** the union-with-overlap-reconciliation whenever history snapshots are whole-state writes. **Adopt** serialized-content hashing for any cross-process dedup. **Adapt** `SUMMARY_PREFIX` to your summarizer's exact artifact text; an append-only substrate can implement `HistorySource` directly via replay and replace this adapter.
