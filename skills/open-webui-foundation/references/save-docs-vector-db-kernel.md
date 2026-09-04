<!-- capsule-v2 -->
# Vector-DB landing kernel — what makes writing document chunks into a vector collection safe?

**Source:** open-webui "Open WebUI License" `main@01f4282f1ffe0d6212f58d3afbeae21fffd0c4be`; Codebase Memory `open-webui`. **Question:** What must a porter check before inserting chunks into a vector store so duplicates, bad splits, cross-file merges, and re-embedding config drift cannot corrupt a collection?

## Chunking + insert kernel
**Path/Symbol:** `backend/open_webui/routers/retrieval.py:save_docs_to_vector_db` (:1620–1827) with helpers `merge_docs_to_target_size` (:1499–1571), `can_merge_chunks` (:1486–1496), `get_splitter_length_function` (:1605–1617).
**Signature:** `def save_docs_to_vector_db(request: Request, docs, collection_name, config: RetrievalConfig, metadata: dict | None = None, overwrite: bool = False, split: bool = True, add: bool = False, user=None) -> bool`
**Data Shape:** docs = LangChain `Document`s; caller metadata ⊕ per-chunk metadata ⊕ `embedding_config:{engine,model}` discriminator stamped on EVERY row; returns bool; raises ValueError (DUPLICATE_CONTENT / EMPTY_CONTENT / invalid splitter) or re-raises embed/insert failures.

### Decisive source
```python
if existing_file_id != metadata.get('file_id'):
    log.info(f'Document with hash {metadata["hash"]} already exists')
    raise ValueError(ERROR_MESSAGES.DUPLICATE_CONTENT)
...
texts = [sanitize_text_for_db(doc.page_content) for doc in docs]           # :1737
metadatas = [{**doc.metadata, **(metadata if metadata else {}),
              'embedding_config': {'engine': config.RAG_EMBEDDING_ENGINE,
                                   'model': config.RAG_EMBEDDING_MODEL}} for doc in docs]
```

**Flow:** (1) if metadata carries `hash`, query the collection filtered by it — an identical hash from a DIFFERENT file_id raises DUPLICATE_CONTENT, same file_id is allowed (re-add/reindex); (2) optional MarkdownHeaderTextSplitter (#…######, strip_headers=False), then `merge_docs_to_target_size` when `CHUNK_MIN_SIZE_TARGET > 0` (:1699–1700); (3) TEXT_SPLITTER ladder: ''/'character'→RecursiveCharacterTextSplitter(add_start_index=True); 'token'→tiktoken encoding VALIDATED before building TokenTextSplitter(disallowed_special); 'token_transformers'→RecursiveCharacter with `get_splitter_length_function`; anything else raises; (4) empty docs ⇒ EMPTY_CONTENT; (5) texts sanitized (`sanitize_text_for_db`, :1737) and every row stamped with embedding_config; (6) lifecycle: exists∧overwrite⇒delete_collection then insert; exists∧¬add⇒silent `return True` no-op; add⇒append into existing; (7) embeddings via `asyncio.run_coroutine_threadsafe(embedding_function(newline-stripped texts, prefix=RAG_EMBEDDING_CONTENT_PREFIX, user), request.app.state.main_loop).result(timeout=RAG_EMBEDDING_TIMEOUT)`; (8) items get uuid4 ids and `VECTOR_DB_CLIENT.insert` — never upsert.
**Flow (merge helper):** undersized chunks absorb the NEXT chunk forward while `can_merge_chunks` holds and merged ≤ CHUNK_SIZE; an undersized tail tries BACKWARD append into the previous emitted chunk; joined with `\n\n`, metadata copied from the original chunk. Boundary guard: sources must be equal; if both sides carry `file_id` they must match; missing ids are allowed to merge.
**Invariant:** the `embedding_config` stamp on each row is the reindex discriminator — rows embedded by another engine/model can be detected later; dedup keys on content HASH scoped by file_id, never on filename.
**Probe:** `grep -n "sanitize_text_for_db(doc.page_content)" backend/open_webui/routers/retrieval.py` → line 1737; `grep -n "CHUNK_MIN_SIZE_TARGET > 0" backend/open_webui/routers/retrieval.py` → 1699.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.get_code_snippet({ project: "open-webui", qualified_name: "open-webui.backend.open_webui.routers.retrieval.save_docs_to_vector_db" });
```
(resolves :1620–1827 verbatim; graph callers_total=0 is an UNDER-COUNT — grep proves production callers in process_file/process_text/process_web_search/process_files_batch.)

## Verdict
Adopt: hash-scoped-by-file dedup gate; splitter validation order (tiktoken validated BEFORE constructing the splitter); embedding_config stamping; silent-no-op vs overwrite vs append collection lifecycle; main-loop bridge with explicit timeout for sync callers. Adapt: `sanitize_text_for_db` rules to your DB; merge bounds to your chunk metrics. Omit: LangChain Document types if your host uses another IR. Coverage caveat: all cited paths report `no_recorded_issue` @ generation 2026-08-24T16:13:21Z; zero test files exist at this pin, evidence is source+graph only.
