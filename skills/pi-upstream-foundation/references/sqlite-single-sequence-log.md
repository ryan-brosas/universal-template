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
**Probe:** `packages/agent/src/harness/session/testing/conformance.ts:96-142` — case "assigns parents and one sequence across every mutation" asserts exact seqs `[entry 1, lane 2, entry 3, record 4, fact 5, fact 6, lane 7]` through `getLog()` for EVERY backend fixture. Deterministic SQL probe executed this pass (see verification.md P3): interleaved entry/record/fact/lane_move inserts replayed in merged seq order. Direct upstream test for the lazy-decode half: `packages/session-backends/sqlite-node/test/log-query.test.ts` ("does not decode rows beyond the requested log limit") corrupts the tail entry's payload to `"not json"` — `getLog({ limit: 1 })` returns only the seq-1 entry and `getLog({ afterSeq: 1, limit: 1 })` returns the seq-2 name fact; the corrupted seq-3 row is never selected into either window and never decoded. Deterministic probe P5 executed this pass (verification.md) reproduces the window arithmetic.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-upstream", query: "getLog merge sequences log items", limit: 10 });
```

## Verdict
Adopt: one counter row per aggregate, one-seq-per-mutation including "boring" mutations like lane moves and facts, lazy-decode merge for pagination. Adapt stream set to your domain. Omit optimistic counters unless you also port multi-writer arbitration — here the lease IS the arbiter. Caveat: `findEntries` with `customType` drops the SQL limit and post-filters after decode (repo.ts:522-533) because custom_type lives inside payload JSON — replicate that quirk consciously.
