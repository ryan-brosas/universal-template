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
**Probe:** deterministic SQL probe P5 executed this pass (verification.md): built the exact DDL on node:sqlite, inserted payloads, verified trigram substring MATCH finds mid-token phrases and the doubled-quote phrasing searches literal quotes. Upstream direct coverage: `test/search.test.ts` exists but was not whole-read this pass (recorded as next-pass witness).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.get_code_snippet({ project: "pi-upstream", qualified_name: "pi-upstream.packages.session-backends.sqlite-node.src.sqlite.search-backend.createSqliteSessionSearch" });
```

## Verdict
Adopt: external-content FTS5 with ai/ad/au triggers, creation-time conditional rebuild, whole-query phrase quoting, bm25 ordering. Adapt tokenizer (trigram suits substring IDE completion; swap for porter/unicode61 for prose recall). Omit persistent connections — stateless per-call open keeps the searcher trivially fork-safe.
