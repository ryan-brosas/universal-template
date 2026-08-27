<!-- capsule-v2 -->
# Derived facts & stats plane — how do you implement latest-value facts with tombstones and derived usage stats over an append-only log?

**Source:** pi-upstream MIT `main@4af9d21d3b4d`; Codebase Memory `pi-upstream`. **Question:** When session metadata (name, labels) and usage stats must be DERIVED from append-only fact/record streams, what SQL shape gives latest-per-key reads, durable clearing, loud decode failure, and correct token/cost accounting?

## Latest-per-(kind,key) facts; NULL-value tombstones remove keys from listings
**Path/Symbol:** `packages/session-backends/sqlite-node/src/sqlite/storage/facts.ts:readLatestFact` (:25–31), `readLatestLabelFacts` (:33–48); schema `facts` (`src/sqlite/migrations/001_initial.sql:96-102`, PK(session_id,seq), nullable key/value).
**Signature:** `readLatestFact(db, sessionId, kind, key): FactRow | undefined`; `readLatestLabelFacts(db, sessionId): { key, value }[]`.
**Data Shape:** every fact is an immutable row `(session_id, seq, kind, key, value)`; the "current value" is a query-time derivation, never a stored column.

### Decisive source
```ts
// facts.ts:25-31 — NULL-safe key match via bound parameter
return sql`SELECT session_id, seq, kind, key, value
	FROM facts INDEXED BY idx_facts_session_kind_key_seq
	WHERE session_id = ${sessionId} AND kind = ${kind} AND key IS ${key}
	ORDER BY seq DESC
	LIMIT 1`.get<FactRow>(db);
```
```ts
// facts.ts:33-48 — current labels: correlated MAX(seq) per key, tombstones excluded
WHERE f.session_id = ${sessionId}
	AND f.kind = 'label'
	AND f.value IS NOT NULL
	AND f.seq = (
		SELECT MAX(candidate.seq) FROM facts AS candidate INDEXED BY idx_facts_session_kind_key_seq
		WHERE candidate.session_id = f.session_id AND candidate.kind = f.kind AND candidate.key IS f.key
	)
ORDER BY f.key
```

**Flow:** set = append one fact row (spending one seq); clear = append a fact row with `value = NULL` (`repo.ts:setName` :618–624 / `setLabel` :631–640); read = latest row per (kind,key) by seq. The sql tag binds null as a parameter, so `key IS ${key}` compiles to `key IS ?` — SQLite's `IS` accepts a bound expression, which is what makes NULL keys (the name fact) comparable without the `= NULL` trap. Label listing filters `value IS NOT NULL` AFTER the per-key MAX, so a cleared label disappears from the listing entirely instead of returning an empty value.
**Invariant:** clearing is a TOMBSTONE ROW, not a DELETE or UPDATE — the fact stream stays append-only and "cleared" remains derivable history. Listings must exclude NULL-valued latest rows; single-key reads must return undefined for them.
**Probe:** `packages/session-backends/sqlite-node/test/facts-query.test.ts` (whole file, 1 case): seeds 7 rows across two sessions including a cleared label (seq 5, value null) and asserts latest-per-key ("new" beats "old"), the NULL-key name read, and label listing `[{entry-1,new},{entry-2,kept}]` with cleared entry-3 absent. Deterministic probe P2 this pass (verification.md) reproduced all three assertions in node:sqlite.

## Cleared names omit the property; corrupted values fail loudly at decode
**Path/Symbol:** `storage/sessions.ts:parseSessionName` (:101–117), `parseMetadata` (:23–40), `decodeSessionMetadata` (:119–131), `readSessionRows` LEFT JOIN (:78–90); `repo.ts:getName` (:613–616).
**Signature:** `decodeSessionMetadata(row, path): SqliteSessionMetadata` — name is a SPREAD property, not a field.

### Decisive source
```ts
// sessions.ts:119-131 — absence, not empty string
const name = row.has_session_name === 0 ? undefined : parseSessionName(row.session_name, row.id);
return { id: row.id, createdAt: row.created_at, ...(name === undefined ? {} : { name }), cwd: row.cwd, path, … };
```
```ts
// sessions.ts:101-117 — null first, then loud type checks
if (value === null) return undefined;
let parsed: unknown;
try { parsed = JSON.parse(value); } catch (error) {
	throw new SessionError("storage", `Invalid SQLite session ${sessionId}: name is not valid JSON`, …);
}
if (typeof parsed !== "string") throw new SessionError("storage", `…: name must be a string`);
```

**Flow:** `readSessionRows`/`readSessionRow` LEFT JOIN each session to its latest name fact (same correlated-MAX pattern, `kind='name' AND key IS NULL`) exposing `has_session_name`/`session_name`; decode maps a NULL value → undefined → property omitted from the metadata object. Both `repo.list()` and `getMetadata()` run the same decode, so corruption is visible on every read surface at once.
**Invariant:** a cleared name is ABSENT from the metadata object — the API cannot distinguish "never named" from "named then cleared" without consulting the fact stream. Corrupted stored JSON is a storage error, never a silent default. Note the split: `has_session_name` means "a name fact EXISTS" (true even after clearing); the omission happens in `parseSessionName`'s null-first branch, not in the JOIN flag.
**Probe:** `repository.test.ts:306-324` (setName(undefined) ⇒ getMetadata() and list()[0] have no `name` property), `:277-304` (stored `"not json"` / `"{}"` name ⇒ list() AND getMetadata() reject "name is not valid JSON" / "name must be a string"), `:253-275` (metadata twin: "metadata is not valid JSON" / "metadata must be an object"). Deterministic probe P3 this pass (verification.md) — first transcription wrongly attributed the omission to the JOIN flag; corrected to the source's null-first branch, then GREEN including both loudness arms.

## Usage stats derive from usage RECORDS, not entries
**Path/Symbol:** `storage/session-stats.ts:addUsageToStats` (:41–50), `incrementMessageCount` (:33–38); call sites `repo.ts:appendEntry` message case (:480), `appendRecord` usage case (:511); schema `session_stats` (`001_initial.sql:32-39`, WITHOUT ROWID).
**Signature:** `addUsageToStats(db, sessionId, usage: Usage): void` — one UPDATE per usage record, inside the record's write transaction.
**Data Shape:** `session_stats(session_id PK, message_count, cached_tokens, uncached_tokens, total_tokens, cost_total)`; seeded at create/fork, mutated only inside lease-renewed write transactions.

### Decisive source
```ts
// session-stats.ts:41-50 — the accounting convention
sql`UPDATE session_stats
	SET cached_tokens = cached_tokens + ${usage.cacheRead},
		uncached_tokens = uncached_tokens + ${usage.input + usage.cacheWrite},
		total_tokens = total_tokens + ${usage.totalTokens},
		cost_total = cost_total + ${usage.cost.total}
	WHERE session_id = ${sessionId}`.run(db);
```

**Flow:** any `usage` record (cause assistant | compaction | branch_summary) appended through `appendRecord` adds its numbers to the stats row in the same transaction; message-type ENTRY appends separately bump message_count (repo.ts:480). Stats are a fold over the record stream — recomputable from scratch by replaying usage records.
**Invariant:** output tokens appear ONLY in total_tokens (totalTokens includes them; cached+uncached do not); cacheWrite counts as UNCACHED; cost accumulates cost.total. A porter who splits input into cached/uncached differently will pass single-provider tests and drift on multi-cause sessions.
**Probe:** `repository.test.ts:411-495` appends assistant (input 100/output 25/cacheRead 40/cacheWrite 10, total 175, cost 0.37), compaction (1/2/3/4, total 10, cost 0.1), branch-summary (5/6/7/8, total 26, cost 0.26) usage records and asserts exactly `{messageCount: 2, cachedTokens: 50, uncachedTokens: 128, totalTokens: 211, costTotal: 0.73}`. Deterministic probe P4 this pass (verification.md) reproduced the arithmetic in node:sqlite — exact match.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-upstream", name_pattern: ".*(readLatestFact|readLatestLabelFacts|addUsageToStats|decodeSessionMetadata)", limit: 10 });
```

## Verdict
Adopt: append-only fact rows with query-time latest-per-(kind,key) derivation, NULL-value tombstones that REMOVE keys from listings, property omission (not empty values) for cleared names, loud decode of corrupted stored JSON on every read surface, and record-driven stats with the cached=cacheRead / uncached=input+cacheWrite / total-includes-output convention. Adapt the stat columns to your metering; keep the fold-over-records shape so stats stay recomputable by replay. Omit per-row value typing beyond JSON-string — the decode layer owns validation. Caveat: CBM MCP was not connected this pass; anchors verified by direct read at pin 4af9d21d plus deterministic node:sqlite probes P2/P3/P4.
