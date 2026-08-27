<!-- capsule-v2 -->
# Session delete/list ACP semantics — how do you implement session/delete and session/list over a file-based store with a secondary discovery source?

**Source:** pi-acp-jetbrain MIT `main@1f0524f777c93c51747c26d24f3609c2a4e6731d`; Codebase Memory `pi-acp`. **Question:** How does an adapter implement idempotent session deletion that survives partial cleanup, project-scoped listing for clients that send no filter, and a store-miss → discovery → backfill resolution order?

## Idempotent delete with retry-preserving failure + scoped listing
**Path/Symbol:** `src/acp/agent.ts` — `deleteSession` (:1558-1588), `listSessions` (:1330-1356), `findStoredSession` (:240-260), `lastSessionCwd` field (:164). Store semantics in `references/session-map-store.md`; discovery walk in `references/session-discovery.md`.
**Signature:** `async deleteSession(params: DeleteSessionRequest): Promise<DeleteSessionResponse>`; `async listSessions(params: ListSessionsRequest): Promise<ListSessionsResponse>`; `private findStoredSession(sessionId: string): { cwd: string; sessionFile: string } | null`.
**Data Shape:** delete response is `{}` on success OR `{ _meta: { piAcp: { deleteError: string } } }` on unlink failure — still HTTP-success-shaped, never a thrown error. List response `{ sessions: SessionInfo[], nextCursor: string | null, _meta: {} }` with `PAGE_SIZE = 50` and an opaque-but-numeric cursor (`String(offset)`).

### Decisive source
```ts
// Per ACP session/delete semantics, deleting a session that does not
// exist (or is already gone) should succeed idempotently.
if (!stored && !piSession) {
  return {}
}
await this.closeManagedSession(params.sessionId)
const sessionFile = stored?.sessionFile ?? piSession?.sessionFile
if (sessionFile) {
  try {
    if (existsSync(sessionFile)) unlinkSync(sessionFile)
  } catch (e) {
    // Report cleanup failures through the reserved _meta extension (P2-8 audit):
    // keep the mapping so a retry can delete the session again.
    return { _meta: { piAcp: { deleteError: `failed to remove session file ${sessionFile}: ${...}` } } }
  }
}
this.store.delete(params.sessionId)
```

**Flow:** deleteSession resolves the session from EITHER the SessionStore OR pi-session discovery (`findPiSession`) — both miss → immediate `{}` (idempotent per ACP spec); otherwise close any live subprocess first, then unlink the session file (store path preferred over discovered path); an unlink THROW returns success-with-`_meta.piAcp.deleteError` WITHOUT deleting the mapping, so a client retry re-resolves and deletes again; only a clean unlink falls through to `store.delete`. listSessions walks ALL pi sessions (`listPiSessions`), filters by `params.cwd ?? this.lastSessionCwd` (Zed sends `{}`, so the last-used cwd emulates pi's project-scoped /resume picker), slices a 50-item page at the numeric cursor offset (invalid cursor → 0), and sets `nextCursor` only when more rows remain. findStoredSession is the backfill seam used by restore/load/fork: store hit wins; store miss → `findPiSession` discovery; a discovery HIT is written back via `store.upsert` so the mapping becomes durable without a separate sync step.
**Invariant:** deletion is idempotent AND retry-safe: the only failure mode that skips `store.delete` is the one where keeping the mapping enables a successful retry; live-subprocess close happens BEFORE file unlink so no running pi can re-append to a deleted session file; listing never invents a cwd filter — absent param means "last session's project", not "everything"; the cursor is opaque to clients but numeric internally, and `nextCursor === null` is the terminal marker.
**Probe:** `node --import tsx --test test/unit/session-delete.test.ts test/component/session-list-scoped.test.ts test/component/session-list-and-load.test.ts` — "deleteSession succeeds idempotently for unknown sessionId" pins `{}` + zero store deletes; "deleteSession finds session via pi discovery when SessionStore misses" pins the discovery fallback + real file unlink; "deleteSession survives missing session file" pins existsSync-guarded unlink; "listSessions defaults to lastSessionCwd when cwd param is omitted" pins the scoped default (2 fixtures in different cwds, only the matching one listed).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-acp", query: "deleteSession listSessions findStoredSession lastSessionCwd", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-source resolution (owned store first, engine-file discovery second, backfill-on-hit), the idempotent-delete-with-retry-preserving-`_meta` contract, and the last-cwd-defaulted scoped listing with numeric cursor pagination. Adapt the `_meta.piAcp.deleteError` namespace and PAGE_SIZE to your protocol's extension surface. Omit the Zed-specific lastSessionCwd emulation if your client always sends cwd. Direct tests executed green at the pin.
