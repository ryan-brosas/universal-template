<!-- capsule-v2 -->
# Session map persistence — corrupt-tolerant versioned JSON store with load-modify-write whole file

**Source:** pi-acp-jetbrain MIT `main@27aac05f`; Codebase Memory `pi-acp`. **Question:** Where does the adapter keep its ACP-session→pi-session-file mapping, and how must a porter handle corruption, schema drift, and concurrent writers?

## Persistent map
**Path/Symbol:** `src/acp/paths.ts` (:9-15) + `src/acp/session-store.ts` whole file (68L): `SessionStore` class (:39-67), `loadFile` (:21-32), `saveFile` (:34-37), `StoredSession` (:5-10).
**Signature:** `new SessionStore(path = getPiAcpSessionMapPath())`; `get(sessionId): StoredSession | null`; `upsert({sessionId, cwd, sessionFile})`; `delete(sessionId)`.
**Data Shape:** `~/.pi/pi-acp/session-map.json` — `{version: 1, sessions: Record<sessionId, {sessionId, cwd, sessionFile, updatedAt}>}`. `getPiAcpDir()` deliberately separates adapter storage from pi's own `~/.pi/agent/*`.

### Decisive source
```ts
function loadFile(path: string): SessionMapFile {
  try {
    const parsed = JSON.parse(readFileSync(path, 'utf-8'))
    if (parsed?.version !== 1 || typeof parsed.sessions !== 'object' || !parsed.sessions)
      return { version: 1, sessions: {} }        // wrong version / malformed shape → treat as EMPTY, not fatal
    return parsed
  } catch { return { version: 1, sessions: {} } } // missing/unparsable → EMPTY; auto-heals on next upsert
}
saveFile: mkdirSync(dirname, {recursive:true}) then writeFileSync(JSON.stringify(data,null,2)+'\n')
```

**Flow:** every operation is a full LOAD-MODIFY-WRITE of the single JSON file — `upsert` stamps `updatedAt: new Date().toISOString()`; `delete` skips the write when the key is absent (idempotent). The store is reconstructed per operation (no in-memory cache), so external edits and multi-process access converge on last-writer-wins instead of serving stale memory.

**Invariant:** NEVER throw on read — any corruption degrades to an empty map and the next successful `upsert` rewrites a valid file (self-healing); this is what makes session restore resilient after a crash mid-write. Schema versioning is check-not-migrate: anything that isn't exactly `version:1` with an object `sessions` resets to empty rather than attempting a migration or crashing. `delete` on unknown id must not create/rewrite the file.

> **SUPERSEDED (pass 3, pin 1f0524f):** upstream added `withFileLock` (mkdir-lock + stale-steal), tmp-rename atomic saves, a corruption stderr note, and the `PI_ACP_SESSION_MAP` override. The "omit locking machinery" verdict below is DEAD at the new pin — see `references/session-store-concurrency.md`, which is now the authoritative capsule for the write path. This capsule remains for its still-valid loadFile/versioning/idempotent-delete detail.

**Probe:** `test/unit/session-restore.test.ts` ("prompt auto-restores a missing session from SessionStore", "setSessionConfigOption auto-restores via pi session discovery when SessionStore misses") and `test/unit/session-delete.test.ts` ("deleteSession succeeds idempotently for unknown sessionId", "deleteSession survives missing session file") pin the consumer-visible contract incl. idempotent delete.
**Coverage:** both files `no_recorded_issue` + `metadata_match`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-acp", query: "SessionStore session-map upsert StoredSession getPiAcpSessionMapPath", limit: 8, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the versioned corrupt-to-empty JSON store with whole-file load-modify-write and idempotent delete. Adapt the storage location and record fields to your host. ~~Omit locking/migration machinery~~ **SUPERSEDED at `1f0524f` (pass 3):** upstream ADDED mkdir-lock concurrency (`withFileLock`, mtime-stale reaping, Atomics.wait sync sleep) and atomic tmp+rename writes after the unlocked design silently dropped sibling-process updates — see session-store-concurrency.md, which is now the authoritative capsule for the write path; THIS capsule remains authoritative for the corrupt-tolerant load/version-gate contract and consumer behavior. Storage location is also env-redirectable via `PI_ACP_SESSION_MAP` (storage-redirect-usage-providers.md).
