<!-- capsule-v2 -->
# Session title index — how does the welcome screen resolve session names from thousands of session files without reading any of them?

**Source:** oh-my-pi (see pack SKILL.md Provenance) MIT `main@4854db85`; Codebase Memory `oh-my-pi`. **Question:** What is the write/backfill/read contract of the `session_titles` SQLite index, and what ownership rules keep it from fighting HistoryStorage over the same database?

## Title-index backfill ladder
**Path/Symbol:** `packages/coding-agent/src/session/title-index.ts:` module-level `recordSessionTitle`/`lookupSessionTitle` (:85–106), `openTitleIndex` (:49–79); consumer `session-listing.ts getRecentSessions` (:662–703); write hook `session-manager.ts:2112-2115`.
**Signature:** `recordSessionTitle(sessionId: string, title: string): void; lookupSessionTitle(sessionId: string): string | undefined`.
**Data Shape:** Table `session_titles (session_id TEXT PRIMARY KEY, title TEXT NOT NULL, updated_at INTEGER DEFAULT epoch-seconds)`; upsert via `ON CONFLICT(session_id) DO UPDATE SET title = excluded.title, updated_at = excluded.updated_at`; module-global `handle` + `failedPath` latch.

### Decisive source
```ts
const useIndex = storage instanceof FileSessionStorage;
for (const { file, stat } of byMtime) {
	if (recent.length >= limit) break;
	const id = useIndex ? sessionIdFromSessionPath(file) : undefined;
	const indexed = id ? lookupSessionTitle(id) : undefined;
	if (indexed) { recent.push({ path: file, name: indexed, timeAgo: formatTimeAgo(stat.mtime) }); continue; }
	const info = await scanSessionFile(file, storage, false);
	if (!info) continue;
	const title = sanitizeSessionName(info.title);
	if (useIndex && title && info.id) recordSessionTitle(info.id, title);   // backfill
	...
}
```

**Flow:** mtime-sorted files → per file: indexed id? → `lookupSessionTitle` hit serves WITHOUT reading content; miss → one header scan (`scanSessionFile`) → sanitized title written back via upsert so NEXT launch skips the read. Writes also flow eagerly from `setSessionName` (only when `#persist && storage instanceof FileSessionStorage`).
**Invariant:** The index is best-effort on BOTH sides: open failures latch `failedPath` (skip retries AND log spam until the db path changes) and record/lookup errors are logged-and-swallowed — a rename must never fail because its index write did. Ownership rules: the table lives in history.db but is NEVER versioned by this module — `PRAGMA user_version` belongs to HistoryStorage's rebuild pass which drops only ITS tables; busy handler must be installed BEFORE any lock-taking statement (#2421). In-memory test storages are excluded by the `instanceof FileSessionStorage` gate so tests never touch the process-wide db.
**Probe:** `test/session/recent-sessions-title-index.test.ts` pins all three legs: `"resolves a titled session from the index without reading file contents"`, `"falls back to a header scan for unindexed files and backfills the index"`, `"orders by file mtime, enforces the limit, and names untitled sessions from their first prompt"`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "recordSessionTitle session_titles history.db title index", limit: 10, fields: ["signature", "name", "file"] });
```
Live-resolved @4854db85: `recordSessionTitle title-index.ts:85-93`, `openTitleIndex :49-79`.

## Verdict
Adopt the read-through-with-backfill ladder and the best-effort failure latches for any "list recent X" surface over per-entity files. Adapt the storage to your host's sqlite layer; keep the never-version-someone-else's-db ownership rule if you co-locate tables. Runner caveat: bun test blocked by pi-natives build in this environment; probe titles verified byte-exact at pin.
