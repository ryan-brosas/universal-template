<!-- capsule-v2 -->
# Directory-index sync & rebuild guard — when does a rebuild re-parse files, what happens to vanished files, and why can build=False refuse to run?

**Source:** paper-qa (Apache-2.0) `main@57e89f7223b0960d5ee5ea048c69e3c47e088572`; Codebase Memory `paper-qa`. **Question:** What exact diff does `get_directory_index` compute between the on-disk index and the paper directory, and under which flags does it remove, warn, re-parse, or hard-fail?

## Connected graph-selected seam
**Path/Symbol:** `src/paperqa/agents/search.py:get_directory_index` (:622-718); `SearchIndex.index_files` (:242-257), `remove_from_index` (:347-359), `save_index`/`changed` reset (:367-379).
**Signature:** `async def get_directory_index(settings: MaybeSettings = None, build: bool = True) -> SearchIndex`.
**Data Shape:** Index identity = `index_settings.name or settings.get_index_name()`; fields = `[file_location, body, title, year]`; `index_files: dict[filename -> filehash | "ERROR"]` persisted zlib+pickle next to the tantivy dir; walk scope = `recurse_subdirectories ? rglob("*") : iterdir()` filtered by `files_filter`.

### Decisive source
```python
if not build:
    if not await search_index.index_files:
        raise RuntimeError(f"Index {search_index.index_name} was empty, please rebuild it.")
    return search_index
...
index_unique_file_paths: set[str] = set((await search_index.index_files).keys())
if extra_index_files := (index_unique_file_paths - {str(f) for f in valid_papers_rel_file_paths}):
    if index_settings.sync_with_paper_directory:
        for extra_file in extra_index_files:
            await search_index.remove_from_index(extra_file)
    else:
        logger.warning(f"Indexed files {extra_index_files} are missing from paper folder ...")
semaphore = anyio.Semaphore(index_settings.concurrency)
... tg.start_soon(process_file, rel_file_path, search_index, manifest, semaphore, _settings, ...)  # per valid file
if search_index.changed: await search_index.save_index()
```

**Flow:** open SearchIndex → optional build=False short-circuit (requires persisted non-empty `index_files`) → load manifest → list valid files → set-diff indexed-minus-valid → remove (or warn-only) extras → bounded-concurrency task group runs `process_file` per valid file (each one skips via `filecheck`) → single final `save_index()` iff anything changed.
**Invariant:** Re-parsing is keyed by FILENAME PRESENCE in `index_files`, not file content — a changed file with the same path is NOT re-indexed unless removed first (`filecheck`'s hash branch only fires for callers that pass `body_filehash`; the directory walk does not). `build=False` must never trigger a rebuild — it raises instead, so a wiped `files.zip` surfaces as "please rebuild" rather than silent empty results. Removal also unlinks the stored blob but its TODO admits directory-embedded hashes make those unlinks usually miss (`missing_ok=True`).
**Probe:** `tests/test_agents.py::test_get_directory_index` (:68-179) — second build patches `Docs.aadd` and asserts NOT awaited; deleting `files.zip` then `get_directory_index(build=False)` raises RuntimeError match "please rebuild"; `::test_empty_index_without_index_rebuild` (:1079-1089) pins the same guard through `agent_query(rebuild_index=False)`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "paper-qa", query: "sync_with_paper_directory remove_from_index changed save_index", limit: 10 });
// trace_path --function-name get_directory_index --direction inbound → build_index, agent_query, paper_search
```

## Verdict
Adopt filename-keyed skip + explicit indexed-vs-directory set diff + changed-flag single-commit close for any resumable corpus indexer; adapt the diff to add content hashing if your sources mutate in place; omit Rich progress plumbing. Coverage caveat: blob-unlink TODO means removal may orphan doc blobs — do not port assuming garbage-free docs/.
