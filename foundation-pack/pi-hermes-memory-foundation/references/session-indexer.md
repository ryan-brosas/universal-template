<!-- capsule-v2 -->
# Session indexing — JSONL parsing, incremental size/mtime backfill, and live-session index

**Source:** pi-hermes-memory (MIT, `main@26f0acaa7741a81ea28eb992ab7ffcfdb7b50a0c`); Codebase Memory `pi-hermes-memory`. **Question:** How does an agent index conversation sessions from JSONL files into SQLite — parsing message blocks (skipping thinking/tool_use, extracting tool calls), incrementally backfilling only changed files newest-first under a cap, and indexing the live in-memory session idempotently?

## Session parser + indexer
**Path/Symbol:** `src/store/session-parser.ts` — `parseSessionFile` (107–172), `getSessionFiles` (181–209), `decodeProjectDir` (215–221), `extractTextContent` (48–82), `extractToolCalls` (87–99). `src/store/session-indexer.ts` — `indexSession` (45–47), `indexSessionOnce` (49–109), `indexChangedSessions` (330–374), `indexAllSessions` (304–321), `indexLiveSession` (216–232), `needsBackfill` (402–422), `touchBackfillTimestamp` (427–434), `getSessionStats` (439–467).
**Signature:** `parseSessionFile(filePath) → ParsedSession | null`; `indexChangedSessions(dbManager, sessionsDir, {projectDir?, maxFilesToIndex?}) → BulkIndexResult`.
**Data Shape:** `ParsedSession = { id, project, cwd, startedAt, endedAt, messages: ParsedMessage[] }`; `ParsedMessage = { id, role: 'user'|'assistant'|'system', content, timestamp, toolCalls? }`. `BulkIndexResult = { sessionsProcessed, sessionsIndexed, sessionsSkipped, messagesIndexed, errors[], reachedLimit? }`. `session_files` stores `(path PK, session_id, size, mtime_ms, indexed_at)` for cheap incremental backfill.

### Decisive source
```ts
// session-parser.ts extractTextContent (48-82): text + tool_result blocks; skip thinking/tool_use
switch (b.type) {
  case 'text': if (typeof b.text === 'string') parts.push(b.text); break;
  case 'thinking': break; // internal reasoning — skip
  case 'tool_use': break; // tracked separately
  case 'tool_result': // include text if present
    if (typeof b.content === 'string') parts.push(b.content);
    else if (Array.isArray(b.content)) for (const item of b.content) if (item?.type === 'text') parts.push(item.text);
}
// extractToolCalls (87-99): assistant-only, collect tool_use/toolCall names

// session-indexer.ts indexSessionOnce (49-109): INSERT OR IGNORE session + messages, update counts
const insertSession = db.prepare('INSERT OR IGNORE INTO sessions (id, project, cwd, started_at, ended_at, message_count) VALUES (?,?,?,?,?,?)');
const insertMsg = db.prepare('INSERT OR IGNORE INTO messages (id, session_id, role, content, timestamp, tool_calls) VALUES (?,?,?,?,?,?)');
// wrapped in db.transaction if available; messagesIndexed = after.count - before.count

// indexChangedSessions (330-374): gather changed set, sort newest-first, apply cap
const changed = [];
for (const file of files) {
  const metadata = getSessionFileMetadata(file);
  if (storedSessionFileMatches(dbManager, metadata)) { result.sessionsSkipped++; continue; }
  changed.push(metadata);
}
changed.sort((a, b) => b.mtimeMs - a.mtimeMs); // crashed sessions (most recent) index first
for (const metadata of changed) {
  if (result.sessionsProcessed >= maxFilesToIndex) { result.reachedLimit = true; break; }
  indexSessionFile(dbManager, metadata.path, result);
}

// needsBackfill (402-422): file count > indexed, OR any file metadata differs, OR timestamp stale (>24h)
```

**Flow:** (1) `parseSessionFile` reads the JSONL, parses `session` entries for id/cwd/timestamp and `message` entries (role-validated, text extracted, tool calls captured for assistant), skipping malformed lines and non-message entry types. (2) `indexSessionOnce` INSERT-OR-IGNOREs the session and messages in a transaction, computing `messagesIndexed` as the delta. (3) `indexChangedSessions` compares stored size/mtime metadata to skip unchanged files, sorts changed files newest-first (so crashed sessions are indexed on the next startup before old history fills the cap), and applies `maxFilesToIndex`. (4) `indexLiveSession` prefers the persisted JSONL file, else `indexCurrentSession` from the in-memory session-manager snapshot. (5) `needsBackfill` decides whether a background backfill should run.

**Invariant:** indexing is idempotent (INSERT OR IGNORE, skipped sessions with zero new messages); unchanged files are skipped without parsing via size/mtime metadata; changed files are processed newest-first under the cap; tool calls are stored as JSON on assistant messages only.

**Probe:** `tests/store/session-indexer.test.ts` — `should index a session and its messages` (:54), `should store tool_calls as JSON` (:74), `should append missing messages for an already-indexed resumed session` (:95), `skips unchanged files using stored size and mtime metadata without parsing them` (:223), `indexes changed files and appends newly persisted messages` (:236), `caps parsed files during startup incremental backfill` (:270), `processes the most recently modified changed files first when the cap is reached` (:282). `tests/store/session-parser.test.ts` — `should skip thinking blocks in assistant messages` (:69), `should extract tool call names from assistant messages` (:95), `should handle malformed JSONL lines gracefully` (:171). Coverage caveat: `tests/` is excluded from the index by design, so probes are source-grounded from the on-disk test files.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-hermes-memory", query: "parseSessionFile indexChangedSessions indexSession indexLiveSession needsBackfill", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the JSONL message parsing (skip thinking/tool_use, extract tool calls), the idempotent INSERT-OR-IGNORE indexing, the size/mtime incremental backfill newest-first under a cap, and the `needsBackfill` heuristic. Adapt the JSONL entry shape, the session-file layout, and the cap constants to the host. Omit the live in-memory session-manager snapshot path and the project-directory name decoding unless a target has them.
