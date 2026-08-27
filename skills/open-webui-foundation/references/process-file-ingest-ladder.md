<!-- capsule-v2 -->
# File ingest endpoint ladder — how does one POST turn a stored file into an embedded collection without exhausting the pool or deadlocking the loop?

**Source:** open-webui "Open WebUI License" `main@01f4282f1ffe0d6212f58d3afbeae21fffd0c4be`; Codebase Memory `open-webui`. **Question:** What is the exact stage order inside `/process/file` that keeps DB connections short, lets failed files retry, and serves three different callers with one body?

## Three-arm ingest endpoint
**Path/Symbol:** `backend/open_webui/routers/retrieval.py:process_file` (:1836–2078), `ProcessFileForm {file_id, content?, collection_name?}`.
**Signature:** `async def process_file(request: Request, form_data: ProcessFileForm, user=Depends(get_verified_user), db: AsyncSession = Depends(get_async_session))`
**Data Shape:** admin fetches any file, others owner-scoped (`get_file_by_id_and_user_id`); explicit `collection_name` requires `_validate_collection_access([name], user, 'write')`, default collection `file-{file.id}`; returns `{status, collection_name, filename, content}` or raises HTTPException.

### Decisive source
```python
# NOTE: save_docs_to_vector_db is a sync function that
# calls asyncio.run_coroutine_threadsafe(..., main_loop).result()
# which blocks the calling thread.  We MUST run it in a
# worker thread to avoid deadlocking the event loop.
result = await run_in_threadpool(save_docs_to_vector_db, request, docs=docs,
                                 collection_name=collection_name, config=config,
                                 metadata={'file_id': file.id, 'name': file.filename, 'hash': hash},
                                 add=(True if form_data.collection_name else False), user=user)
...
    # Clear the hash so the file can be re-uploaded after fixing the issue   # :2063
    await Files.update_file_hash_by_id(file.id, None, db=session)
```

**Flow:** (1) resolve file (admin-any / user-owned); (2) pick collection (validated write access for explicit names); (3) THREE content arms — form `content` supplied: best-effort delete of `file-{id}` collection except-pass (audio pipeline) + single `<br/>`→`\n` Document; `collection_name` set (knowledge add/update): COPY-REUSE existing chunks from `file-{id}` verbatim (query filter file_id), falling back to stored `data.content`; else fresh loader: `Storage.get_file` via to_thread → `build_loader_from_config().aload` → filter_metadata + name/created_by/file_id/source stamps; (4) persist text_content + sha256 hash; (5) `BYPASS_EMBEDDING_AND_RETRIEVAL` short-circuits to completed + RETRIEVAL_CONTENT_PROCESSED(collection_name=None); (6) otherwise `db.commit()` BEFORE the slow step ("Commit any pending changes before the slow embedding step"), embed via worker thread (see excerpt), `add=True` iff knowledge path; (7) success writes metadata.collection_name + status completed + hash through a FRESH session and publishes RETRIEVAL_CONTENT_PROCESSED; (8) failure logs.exception, fresh session sets status failed AND clears the hash so a fixed file can be re-uploaded past the dedup gate; `'No pandoc was found'` → 400 PANDOC_NOT_INSTALLED.
**Invariant:** no pooled DB connection is held across the 5–60s embedding call (commit-first + fresh-session updates); a failed ingest must NEVER leave a stale hash behind — the dedup gate in save_docs would otherwise block every retry as DUPLICATE_CONTENT.
**Probe:** `grep -n "which blocks the calling thread" backend/open_webui/routers/retrieval.py` → line 1999; `grep -n "so the file can be re-uploaded after fixing" backend/open_webui/routers/retrieval.py` → line 2063.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "open-webui", name_pattern: ".*process_file.*", limit: 20 });
```
(resolves `process_file` :1837–2078 and `process_files_batch` :3011–3126.)

## Verdict
Adopt: commit-before-external-call + fresh-session completion writes; failure = status+hash-clear pairing; copy-reuse arm that re-embeds stored chunks instead of re-parsing bytes. Adapt: collection naming scheme and validation hook to your ACL model. Omit: specific loader config plumbing. Coverage caveat: cited ranges verified by direct read at this pin; graph trace inbound callers_total=5 includes knowledge router handlers and files-router content updates; zero test files exist at this pin.
