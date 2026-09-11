<!-- capsule-v2 -->
# Knowledge document-listing surface — how does a porter enumerate indexed docs by scope, and what invariants (deleting-hiding, session-thread gating, preview shape) must hold?

**Source:** cuga-agent (Apache-2.0) `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** A porter wiring a knowledge-browser or prompt doc-inventory needs the exact chain that lists documents per scope, the data shape each layer returns, and the invariants (hiding `deleting` docs, requiring a thread for session scope, preview truncation) — and should know that there is NO `list_collections` engine method; the listing surface is `list_documents` only.

## Scope-resolved document listing chain
**Path/Symbol:** `src/cuga/backend/knowledge/engine.py` `KnowledgeEngine.list_documents` (3679-3684) + `get_document_file_path` (3686-3693); `metadata/sqlite_store.py` `SqliteKnowledgeMetadata.list_documents` (108-114); `metadata/postgres_store.py` `PostgresKnowledgeMetadata.list_documents` (127-132); `client.py` `KnowledgeClient.list_documents` (332-349); `routes.py` `list_documents` (672-712). `DocInfo` dataclass at engine.py 750-756.
**Signature:** `async def list_documents(self, collection: str) -> list[DocInfo]` (engine); `async def list_documents(scope="agent", thread_id=None) -> list[dict]` (client); route `GET /documents?scope=agent` with `Depends(require_internal_or_auth)`.
** Data Shape:** `DocInfo(filename, chunk_count, status, ingested_at)`; the route additionally exposes `preview`. Metadata store rows: `SELECT filename, chunk_count, status, ingested_at, preview FROM documents WHERE collection=? AND status != 'deleting' ORDER BY ingested_at DESC`. Client returns a list of `{filename, chunk_count, status, ingested_at, preview}` dicts.

### Decisive source
```python
# engine.py — sanitize collection, hide 'deleting', map rows to DocInfo
async def list_documents(self, collection: str) -> list[DocInfo]:
    await self._ensure_metadata_ready()
    collection = _sanitize_collection(collection)      # [^a-zA-Z0-9_] -> _
    rows = await self._metadata.list_documents(collection)
    return [DocInfo(**r) for r in rows]

def get_document_file_path(self, collection, filename) -> Path:
    collection = _sanitize_collection(collection)
    filename = _sanitize_filename(filename)
    file_path = self._files_dir / collection / filename
    if not file_path.exists():
        raise DocumentNotFoundError(filename)
    return file_path

# sqlite_store.py — the 'deleting' hide is at the query level
SELECT filename, chunk_count, status, ingested_at, preview FROM documents
WHERE collection=? AND status != 'deleting' ORDER BY ingested_at DESC

# routes.py — session scope without a thread is a 400, not an empty list
if scope == "session" and not (identity.thread_id or "").strip():
    raise HTTPException(status_code=400,
        detail="X-Thread-ID required for scope=session (cannot list session documents ...)")
```

**Flow:** route resolves `scope` (agent/session) → `resolve_collection(identity, scope, request)` → `engine.list_documents(collection)` → `_ensure_metadata_ready` → `_sanitize_collection` → metadata store query (hides `deleting`, newest-first) → `[DocInfo(**r)]` → route projects to `{filename, chunk_count, status, ingested_at, preview}`. Session scope with no thread → 400; session scope that comes back empty logs a diagnostic (collection name + truncated thread id) to catch search/list divergence. `get_knowledge_summary` (awareness.py 237-256) consumes `engine.list_documents` for the agent (permanent) and session (temporary) doc inventory, driving the cross-scope commit gate.
**Invariant:** `deleting` documents are never listed (hiding is at the SQL `status != 'deleting'` level, so a mid-delete doc can't appear in the inventory or prompt); collection and filename are sanitized (`[^a-zA-Z0-9_]` → `_`) before any path/query construction; session scope REQUIRES a thread id (400, not empty — rules out a silent empty list when the conversation wasn't identified); file-path retrieval raises `DocumentNotFoundError` for missing originals.
**Probe:** `tests/unit/test_knowledge_routes.py` — `test_list_documents_rejects_disabled_session_scope` (403) and `test_list_documents_rejects_disabled_agent_scope` (403) pin scope gating; the `_FileEngine`/`_FakeEngine` stubs implement `list_documents`/`get_document_file_path`. `tests/integration/test_knowledge_integration.py` `TestSDKClient.test_client_list_documents` (385-397) pins the SDK client path. `tests/unit/test_knowledge_session_isolation.py` `_IsolatingFakeEngine.list_documents` (191-194) pins session isolation. Coverage caveat: the `deleting`-hide and `ORDER BY ingested_at DESC` are pinned by the SQL in the store, not a dedicated unit test asserting the filter.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "list_documents get_document_file_path DocInfo", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the scope-resolved listing chain (route → client → engine → metadata store), the `DocInfo`/preview shape, the `deleting`-hide at the query level, the session-requires-thread 400 (never an empty list), and the sanitize-before-query/path rule; adapt the collection-naming scheme, the `_files_dir` layout, and the preview truncation to your host; omit `list_collections` — it does not exist as an engine method (the pass-12 target's "list_collections" was aspirational; the real surface is `list_documents` plus the store's `get_deleting_documents` for cleanup). Direct tests cover scope gating and the SDK path; the `deleting`-hide filter is source-confirmed at the SQL level.
