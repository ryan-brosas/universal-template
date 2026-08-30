<!-- capsule-v2 -->
# KB metadata embedding maintenance — how do you give collection objects searchable self-descriptions without leaking failures?

**Source:** open-webui "Open WebUI License" `main@01f4282f1ffe0d6212f58d3afbeae21fffd0c4be`; Codebase Memory `open-webui`. **Question:** How should a system embed its own object metadata (name/description) into a fixed catalog collection, and what failure posture keeps admin reindexing safe?

## Fixed-collection upsert trio
**Path/Symbol:** `backend/open_webui/routers/knowledge.py:embed_knowledge_base_metadata` (:68–94), `remove_knowledge_base_metadata_embedding` (:97–107), `reindex_knowledge_base_metadata_embeddings` (:416–437).
**Signature:** `async def embed_knowledge_base_metadata(request, knowledge_base_id: str, name: str, description: str) -> bool` / `async def remove_knowledge_base_metadata_embedding(knowledge_base_id: str) -> bool` / `POST /metadata/reindex (admin)`.
**Data Shape:** content = `f'{name}\n\n{description}'` when a description exists else just name; item `{id: kb_id, text, vector, metadata:{knowledge_base_id}}`; both mutators return bool and NEVER raise.

### Decisive source
```python
KNOWLEDGE_BASES_COLLECTION = 'knowledge-bases'
...
    embedding = await request.app.state.EMBEDDING_FUNCTION(content, prefix=RAG_EMBEDDING_CONTENT_PREFIX)
    await ASYNC_VECTOR_DB_CLIENT.upsert(collection_name=KNOWLEDGE_BASES_COLLECTION, items=[...])
    return True
except Exception as e:
    log.error(f'Failed to embed knowledge base {knowledge_base_id}: {e}')
    return False
```

**Flow:** embed builds the description text, calls the app-level embedding function with the standard content prefix, UPSERTs into the one fixed `knowledge-bases` catalog collection keyed by the stable kb id; removal deletes by id in the same collection; the admin `POST /metadata/reindex` loops every KB awaiting one embed each and returns honest counts `{'total', 'success'}`.
**Invariant:** catalog writes are UPSERT-by-stable-id (unlike chunk inserts which are insert-only uuid4); failures are fail-soft (log + False) so a broken embedding backend degrades discovery, never CRUD; the reindex endpoint deliberately does NOT take `Depends(get_async_session)` — its own docstring records that N external embedding calls while holding a session would exhaust the connection pool.
**Probe:** `grep -n "would exhaust the connection pool" backend/open_webui/routers/knowledge.py` → 426; `grep -n "KNOWLEDGE_BASES_COLLECTION = " backend/open_webui/routers/knowledge.py` → 65.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "open-webui", name_pattern: ".*knowledge_base_metadata.*", limit: 20 });
```
(resolves all three nodes :68–94 / :97–107 / :417–437 plus their callers — create/update/external twins and the reindex loop.)

## Verdict
Adopt: one fixed catalog collection with stable-id upsert; fail-soft metadata embeddings decoupled from object CRUD; session-free admin reindex with counted partial success. Adapt: prefix constant and content template to your embedding config. Omit: the specific six-caller wiring (create/update/external-source paths). Coverage caveat: direct reads at this pin; zero test files exist; callers_total=6 confirmed by trace (create_external_knowledge, create_external_knowledge_source, create_new_knowledge, reindex twin, update_external_knowledge_source, update_knowledge_by_id).
