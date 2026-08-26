<!-- capsule-v2 -->
# Per-file indexing error taxonomy — what happens when ONE file fails mid-build of thousands, and how does the next run resume?

**Source:** paper-qa (Apache-2.0) `main@57e89f7223b0960d5ee5ea048c69e3c47e088572`; Codebase Memory `paper-qa`. **Question:** Which parse failures are swallowed vs fatal in `process_file`, why does a failed file get an immediate index save, and how is batched committing counted across concurrent tasks?

## Connected graph-selected seam
**Path/Symbol:** `src/paperqa/agents/search.py:process_file` (:490-580); `SearchIndex.filecheck` (:263-269), `mark_failed_document` (:271-273); `FAILED_DOCUMENT_ADD_ID = "ERROR"` (:487).
**Signature:** `async def process_file(rel_file_path: anyio.Path, search_index: SearchIndex, manifest: dict, semaphore: anyio.Semaphore, settings: Settings, processed_counter: Counter[str], progress_bar_update: Callable | None) -> None`.
**Data Shape:** Each file becomes one tantivy doc `{title, year, file_location, body}` plus a stored blob = the whole temporary `Docs` object (all chunks + DocDetails). `processed_counter["batched_save_counter"]` counts successes ACROSS concurrent tasks toward `settings.agent.index.batch_size`.

### Decisive source
```python
try:
    await tmp_docs.aadd(path=abs_file_path, fields=["title", "author", "journal", "year"], ...)
except Exception as e:
    # 1. save_index so we can resume without rebuilding this file if a separate
    #    process_file invocation leads to a segfault or crash. 2. don't deadlock.
    await search_index.mark_failed_document(file_location)   # index_files[path] = "ERROR"; changed=True
    await search_index.save_index()
    if not isinstance(e, ValueError | ImpossibleParsingError):
        raise      # unexpected → kills the task group as ExceptionGroup
    return         # expected parse/value failure → skip this file only
this_doc = next(iter(tmp_docs.docs.values()))
title = this_doc.title or fallback_title if isinstance(this_doc, DocDetails) else fallback_title
await search_index.add_document({...}, document=tmp_docs)
processed_counter["batched_save_counter"] += 1
if processed_counter["batched_save_counter"] == settings.agent.index.batch_size:
    await search_index.save_index(); processed_counter["batched_save_counter"] = 0
```

**Flow:** semaphore-acquired → `filecheck(filename)` skip gate → manifest kwargs injection → fresh `Docs()` per file (`aadd` runs the full ingest pipeline incl. metadata upgrade) → success adds doc + batched commit; expected failure marks ERROR + immediate commit and returns; unexpected failure marks ERROR + commits then re-raises.
**Invariant:** A filename marked `"ERROR"` IS present in `index_files`, so the next build's `filecheck` treats it as DONE — resume means "don't re-parse failures", NOT "retry them" (retrying requires deleting the entry or changing the path). The immediate save after failure exists so a hard crash (segfault of a native parser) still persists everything learned before it. Batched saves are not atomic against concurrency — the counter can overshoot `batch_size` under racing tasks; correctness relies on tantivy's atomic commit, not on exact batch boundaries.
**Probe:** `tests/test_agents.py::test_resuming_crashed_index_build` (:183-234) — crashes the 4th `Docs.aadd` (ExceptionGroup "unhandled"), then resumes and asserts full file count with `mock_aadd.await_count < num_source_files`; `::test_get_directory_index` (:97-100) counts `sum(id_ != FAILED_DOCUMENT_ADD_ID ...) == 12` because empty.txt legitimately fails.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "paper-qa", query: "process_file mark_failed_document FAILED_DOCUMENT_ADD_ID batched_save_counter", limit: 10 });
// trace_path --function-name process_file --direction outbound → Docs.aadd, add_document, save_index
```

## Verdict
Adopt the ERROR-tombstone resume protocol and the swallow-list (domain parse errors skip; anything else is a bug and should surface), for any fan-out indexer over untrusted inputs; adapt the tombstone to include a retry-count or timestamp if you want bounded retries — upstream deliberately has none; omit the Docs-object blob storage if you only need text. Coverage caveat: all cited paths `no_recorded_issue` + `metadata_match`; concurrency behavior pinned by test assertions, not a live race run in this environment.
