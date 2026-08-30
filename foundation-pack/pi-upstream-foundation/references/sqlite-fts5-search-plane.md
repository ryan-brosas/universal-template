<!-- capsule-v2 -->
# FTS5 external-content search plane — how do you full-text-search session entries co-located in the canonical DB without a sync pipeline or stale index?

**Source:** pi-upstream MIT `main@4af9d21d3b4d`; Codebase Memory `pi-upstream`. **Question:** How does an FTS index stay perfectly aligned with rows it doesn't own, and how must user text be quoted before MATCH?

## External-content FTS5 + sync triggers + one-shot rebuild + phrase-quote-everything
**Path/Symbol:** `packages/session-backends/sqlite-node/src/sqlite/search-backend.ts:ensureSearchSchema` (:65–89) and `SqliteSessionSearch.search` (:135–189).
**Signature:** `search(text: string, options?: SessionSearchOptions): AsyncIterable<SqliteSessionSearchHit>`; hits carry `{sessionId, metadata, entryId, timestamp, score}`.
**Data Shape:** virtual table `session_search_fts(payload, content='entries', content_rowid='rowid', tokenize='trigram remove_diacritics 1')`; per-call open/applyMigrations/ensureSchema/close — the searcher holds NO persistent connection.

### Decisive source
```sql
CREATE VIRTUAL TABLE IF NOT EXISTS session_search_fts USING fts5(
  payload,
  content = 'entries',
  content_rowid = 'rowid',
  tokenize = 'trigram remove_diacritics 1'
);
CREATE TRIGGER IF NOT EXISTS session_search_fts_ai AFTER INSERT ON entries BEGIN
  INSERT INTO session_search_fts(rowid, payload) VALUES (new.rowid, new.payload);
END;
-- plus _ad (delete) and _au (update-of-payload) triggers writing ('delete', old.rowid, old.payload)
...
if (!ftsExists && entriesExist) rebuildSearchIndex(db); -- INSERT INTO session_search_fts(session_search_fts) VALUES('rebuild')
```
```ts
const query = `"${queryText.replaceAll('"', '""')}"`;
```

**Flow:** open → migrations → ensureSearchSchema inside ONE transaction: create FTS + three sync triggers if absent; if the FTS table is NEW but `entries` already exist, issue the special `'rebuild'` command once so pre-existing rows enter the index → query: trim text, reject empty / non-positive limit / empty entryTypes, honor abort signal before and during iteration → wrap the ENTIRE trimmed string as one double-quoted phrase with inner quotes doubled → join FTS→entries on rowid→sessions, LEFT JOIN latest name fact via correlated MAX(seq) → order by bm25() ascending, LIMIT (default -1) → yield hits lazily from an iterator, checking the signal per row, closing the db in finally.
**Invariant:** index consistency is delegated to SQLite's external-content machinery + triggers executing in the writer's transaction — no background indexer, no reconciliation loop; a fresh index beside existing data self-heals exactly once at creation.
**Probe:** deterministic SQL probe P5 executed this pass (verification.md): built the exact DDL on node:sqlite, inserted payloads, verified trigram substring MATCH finds mid-token phrases and the doubled-quote phrasing searches literal quotes. Upstream direct coverage: `test/search.test.ts` whole-read this pass — full 14-case inventory in the lazy-initialization section below.

## Lazy initialization; once initialized, index health IS write availability
**Path/Symbol:** `search-backend.ts:SqliteSessionSearch.search` early-return gate (:135–138) and `openDatabase` fail-closed close (:116–133); witnesses `test/search.test.ts` (:211–231 lazy init, :233–252 append rollback, :254–276 delete rollback, :278–289 setup-failure close, :66–81 cleared-name omission).
**Signature:** unchanged — `search(text, options?)`; the new invariant is about WHEN the schema appears and what breaks when it vanishes.

### Decisive source
```ts
async *search(text: string, options: SessionSearchOptions = {}) {
	const queryText = text.trim();
	if (!queryText || (options.limit !== undefined && options.limit <= 0)) return;
	if (options.entryTypes?.length === 0) return;
	throwIfAborted(options.signal);
	const db = await this.openDatabase();   // configure → applyMigrations → ensureSearchSchema
```
```ts
// openDatabase (:124-132) — setup failure closes the just-opened handle before rethrowing
try {
	configureSqliteDatabase(db);
	await applyMigrations(db);
	ensureSearchSchema(db);
	return db;
} catch (error) {
	db.close();
	throw error;
}
```

**Flow:** `ensureSearchSchema` is reachable ONLY through the search path — canonical writes never create the FTS table (test :211–231 asserts `session_search_fts` absent from `sqlite_master` after an appendMessage, and a blank search `"  "` returns [] without initializing anything). A deployment that never searches pays zero index cost. But the first non-blank search creates table + ai/ad/au triggers, and from then on every INSERT / DELETE / UPDATE-OF-payload on `entries` fires a trigger writing into `session_search_fts` INSIDE the writer's transaction — so if the FTS table disappears (e.g. `DROP TABLE`), the next canonical append rejects and rolls back wholesale (test :233–252: `entries` stays empty) and `repository.delete` likewise rejects leaving the session intact (:254–276). Initialization is a one-way latch: the search plane is opt-in, then sticky, coupling index health to write availability. Search-side setup failure closes the handle before rethrowing (test :278–289, `counts.closes === 1`) — the same fail-closed split as the repository's `openDatabase`. Hit metadata omits cleared session names: the correlated MAX(seq) name-fact join excludes tombstones (test :66–81 asserts no `name` property on hits).
**Invariant:** writes must remain correct with the FTS plane absent (lazy init), and once present, trigger failure must abort the whole writer transaction rather than leave canonical rows desynchronized from the index.
**Probe:** full 14-case inventory of `test/search.test.ts` read this pass: trigram substring match incl. "uth" (:23); cleared-name omission (:66); quoted text `'missing "phrase"'` → [] without FTS syntax exposure (:83); rebuild-on-first-init (:95); entry-type filter (:113); limits incl. limit 0 → [] (:132); session-delete removes hits (:151); post-init trigger index/remove (:170); direct `DELETE FROM entries` removes via trigger (:190); lazy init (:211); append rollback on trigger failure (:233); delete rollback (:254); setup-failure close (:278); pre-session search initializes canonical storage and returns [] (:291). Deterministic probes P3 executed this pass (verification.md): append succeeds while FTS absent; after latch creation, DROP TABLE makes the next insert abort with `entries` unchanged.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.get_code_snippet({ project: "pi-upstream", qualified_name: "pi-upstream.packages.session-backends.sqlite-node.src.sqlite.search-backend.createSqliteSessionSearch" });
```

## Verdict
Adopt: external-content FTS5 with ai/ad/au triggers, creation-time conditional rebuild, whole-query phrase quoting, bm25 ordering — and the lazy-init gate (schema only on first non-blank search) plus the rollback-coupling test: if you port the triggers, a dropped or corrupt FTS table must fail writes loudly, not drift. Adapt tokenizer (trigram suits substring IDE completion; swap for porter/unicode61 for prose recall). Omit persistent connections — stateless per-call open keeps the searcher trivially fork-safe.
