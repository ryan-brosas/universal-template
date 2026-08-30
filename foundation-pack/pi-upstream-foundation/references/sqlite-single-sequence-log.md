<!-- capsule-v2 -->
# Single-sequence merged log — how does a session keep ONE total order across entries, records, lane moves, and facts so the log can be replayed and paged?

**Source:** pi-upstream MIT `main@4af9d21d3b4d`; Codebase Memory `pi-upstream`. **Question:** How do four different mutation streams share one sequence space without gaps or compare-and-set machinery, and how does a paginated log merge them cheaply?

## One counter row per session; every mutation spends exactly one seq; merge sorts thunks, decodes lazily after limit
**Path/Symbol:** `packages/session-backends/sqlite-node/src/sqlite/storage/session-sequences.ts` (:5–29) + `repo.ts:SqliteSessionStorage.getLog` (:568–611); schema `UNIQUE(session_id, seq)` on `entries`/`records`, PK(session_id,seq) on `lane_moves`/`facts`.
**Signature:** `getNextSequence(db, sessionId): number`; `advanceSequence(db, sessionId, seq)` (writes next = seq+1); `getLog(options?: { afterSeq?: number; limit?: number }): Promise<LogItem[]>`.
**Data Shape:** LogItem kinds: `entry | record | lane | fact`. The counter is one row in `session_sequences(next_seq)` created at session create/fork.

### Decisive source
```ts
const logRows: { seq: number; decode: () => LogItem }[] = [
	...entryRows.map((row) => ({ seq: row.seq, decode: () => ({ kind: "entry" as const, seq: row.seq, entry: decodeEntry(row) }) })),
	...recordRows.map((row) => ({ seq: row.seq, decode: () => ({ kind: "record" as const, seq: row.seq, record: decodeRecord(row) }) })),
	...laneRows.map((row) => ({ seq: row.seq, decode: () => ({ kind: "lane" as const, seq: row.seq, lane: row.lane, leafId: row.leaf_id }) })),
	...factRows.map((row) => ({ /* name/label fact projection */ })),
].sort((left, right) => left.seq - right.seq);
const selectedRows = options.limit === undefined ? logRows : logRows.slice(0, options.limit);
return selectedRows.map((row) => row.decode());
```

**Flow:** every write takes the pattern read-counter → use seq → advance (e.g. `appendEntry` :456–484 inserts entry + swings lane leaf + appends cache row + bumps message stat + advances, ALL in one lease-renewed transaction; `createLane`/`moveLane` spend a seq on an auditable `lane_moves` row; `setName`/`setLabel` append fact rows) → reads page each stream with `seq > afterSeq ORDER BY seq LIMIT n` → merge by sorting lightweight `{seq, decode}` thunks and decoding only the first `limit` winners.
**Invariant:** there is NO compare-and-set on the counter (`advanceSequence` blindly writes seq+1) — gap-free monotonicity rests entirely on the two-level single-writer discipline (fenced lease × serial queue × one transaction). Schema backs it with UNIQUE(session_id,seq). Consequence: fork RENUMBERS copied entries 1..n via `allocateSeq` because sequence identity belongs to the session, not to entries.

## Cursor semantics — per-stream LIMIT, then global merge-slice; validation lives in the facade, not the backend
**Path/Symbol:** `repo.ts:SqliteSessionStorage.getLog` (:568-611) with per-stream readers `readEntryRows` (`storage/entries.ts:39-62`), `readRecordRows` (`storage/records.ts:46`), `readLaneMoveRows` (`storage/lanes.ts:102`), `readFactRows` (`storage/facts.ts:49-60`); facade validation `packages/agent/src/harness/session/session.ts:30-39, :266-268` and the scan twin `state.ts:31-39`.
**Flow:** each of the four streams is read independently with `seq > afterSeq ORDER BY seq LIMIT n` (the same exclusive-cursor shape as `findEntries`) → the merged `{seq, decode}` thunk list is sorted by seq → `logRows.slice(0, limit)` selects the global page BEFORE any decode → only selected thunks decode. With a limit, each stream contributes at most n rows and the page is the first `limit` items by seq — correct because every stream is seq-ascending from the same afterSeq, so no excluded row can sort before an included one.
**Invariant:** the SQLite backend performs NO argument validation — `afterSeq >= 0` and positive-integer limit are enforced once in the Session facade (`assertValidCursor`/`assertValidLimit`, throwing `invalid_query`), mirroring the write path where the facade owns payload validation and backends own transactional durability. The conformance suite pins the split cross-backend: `getLog({ afterSeq: -1 })` rejects `invalid_query` (conformance.ts:247) while the backend code path contains no check at all.
**Probe:** `packages/agent/src/harness/session/testing/conformance.ts:247` (invalid cursor rejected before any read); deterministic probe P3 this pass (verification.md): four-stream fixture paged with `afterSeq=2, limit=3` returns exactly seqs 3-5 with rows 6+ never decoded.
**Probe:** `packages/agent/src/harness/session/testing/conformance.ts:96-142` — case "assigns parents and one sequence across every mutation" asserts exact seqs `[entry 1, lane 2, entry 3, record 4, fact 5, fact 6, lane 7]` through `getLog()` for EVERY backend fixture. Deterministic SQL probe executed this pass (see verification.md P3): interleaved entry/record/fact/lane_move inserts replayed in merged seq order. Direct upstream test for the lazy-decode half: `packages/session-backends/sqlite-node/test/log-query.test.ts` ("does not decode rows beyond the requested log limit") corrupts the tail entry's payload to `"not json"` — `getLog({ limit: 1 })` returns only the seq-1 entry and `getLog({ afterSeq: 1, limit: 1 })` returns the seq-2 name fact; the corrupted seq-3 row is never selected into either window and never decoded. Deterministic probe P5 executed this pass (verification.md) reproduces the window arithmetic.

## customType post-filter: the canonical-entries scan drops the SQL limit and re-filters after decode; the branch-cache path does not
**Path/Symbol:** `repo.ts:SqliteSessionStorage.findEntries` (:522-533) + `repo.ts:matchesEntryQuery` (:312-320); contrast `findEntriesOnBranch` (:535-549) with the materialized column `branch_entries.custom_type` (`migrations/001_initial.sql:49`, index at :56).
**Signature:** `sqlType = query.type ?? (query.customType === undefined ? undefined : "custom")`; `sqlLimit = query.customType === undefined ? query.limit : undefined`.

### Decisive source
```ts
async findEntries(query: EntryQuery = {}): Promise<Entry[]> {
	const sqlType = query.type ?? (query.customType === undefined ? undefined : "custom");
	const sqlLimit = query.customType === undefined ? query.limit : undefined;
	const rows = readEntryRows(this.db, this.metadata.id, { cursor: query.cursor, limit: sqlLimit, order: query.order, type: sqlType });
	const entries = rows.map(decodeEntry).filter((entry) => matchesEntryQuery(entry, query));
	return query.limit === undefined ? entries : entries.slice(0, query.limit);
}
```

**Flow:** a customType query narrows the SQL scan to `type = "custom"` but CANNOT push the customType predicate into SQL — `custom_type` lives inside the entries table's payload JSON, so the SQL layer would need a decode to evaluate it. The SQL limit is therefore dropped whenever customType is set (a SQL limit could truncate BEFORE the post-filter and lose matching rows), rows are decoded, `matchesEntryQuery` re-filters on customType (and re-applies cursor direction in JS: `entry.seq > afterSeq` oldest-first / `< afterSeq` newest-first), and only then `entries.slice(0, query.limit)` applies the limit. The branch-cache read (`findEntriesOnBranch`) has no such quirk: `branch_entries` carries a materialized `custom_type` column with its own index, so `b.custom_type = ?` filters in SQL and the limit stays in SQL.
**Invariant:** a filter column that exists only inside JSON forces a two-stage query — SQL narrows by the structural type, JS filters by the embedded value, and the SQL limit MUST be dropped or the post-filter can silently lose rows. The materialized-column path (branch cache) is the escape hatch: denormalizing the embedded field into an indexed column restores single-stage SQL filtering.
**Probe:** deterministic probe P3 this pass (verification.md) — transcribed two-stage filter on a fixture with 5 custom entries of two customTypes plus 2 messages: customType query returns exactly the matching customs, SQL limit dropped (no truncation), JS slice enforces the final limit; the branch-cache twin with the materialized column filters in SQL with the limit intact.

## Verdict
Adopt: one counter row per aggregate, one-seq-per-mutation including "boring" mutations like lane moves and facts, lazy-decode merge for pagination, and per-stream LIMIT before the global merge-slice; keep query-shape validation in the facade so backends stay thin. Adapt stream set to your domain. Omit optimistic counters unless you also port multi-writer arbitration — here the lease IS the arbiter. Caveat: `findEntries` with `customType` drops the SQL limit and post-filters after decode (repo.ts:522-533) because custom_type lives inside payload JSON — replicate that quirk consciously.
