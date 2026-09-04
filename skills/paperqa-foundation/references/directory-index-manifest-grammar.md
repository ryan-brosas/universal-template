<!-- capsule-v2 -->
# Directory-index manifest grammar — how do I seed trusted metadata into an index build without LLM calls, and what happens when the manifest is broken?

**Source:** paper-qa (Apache-2.0) `main@57e89f7223b0960d5ee5ea048c69e3c47e088572`; Codebase Memory `paper-qa`. **Question:** Which file formats/keys does the paper-directory manifest accept, how are rows matched to files under relative vs absolute paper directories, and does a broken manifest fail the build?

## Connected graph-selected seam
**Path/Symbol:** `src/paperqa/agents/search.py:maybe_get_manifest` (:448-484), `fetch_kwargs_from_manifest` (:437-445); `src/paperqa/settings.py:IndexSettings.finalize_manifest_file` (:607-613).
**Signature:** `async def maybe_get_manifest(filename: anyio.Path | None = None) -> dict[str, dict[str, Any]]`; `def fetch_kwargs_from_manifest(file_location: str, manifest: dict[str, Any], manifest_fallback_location: str) -> dict[str, Any]`.
**Data Shape:** CSV keyed by `file_location` column → row dict of DocDetails-compatible fields (title, doi, authors, year, …). Returned map is `{str(file_location): record}`; empty/unreadable manifest ⇒ `{}` (build continues).

### Decisive source
```python
if filename.suffix == ".csv":
    ...
    reader_kwargs: dict[str, Any] = {}
    if sys.version_info >= (3, 12):  # Unlocks `bool | None` fields
        reader_kwargs["quoting"] = csv.QUOTE_NOTNULL
    file_loc_to_records = {str(r.get("file_location")): r for r in csv.DictReader(...) if r.get("file_location")}
except FileNotFoundError: logger.warning(...)
except Exception:        logger.exception(...)
else: return file_loc_to_records
...
manifest_entry = manifest.get(file_location) or manifest.get(manifest_fallback_location)
if manifest_entry:
    return DocDetails(**manifest_entry).model_dump()   # bad rows die HERE at model construction
return {}
```

**Flow:** `finalize_manifest_file` resolves the configured name to an absolute path → `maybe_get_manifest` parses it (CSV ONLY; other suffixes log an error and return `{}`) → per-file lookup tries the primary location string then its absolute↔relative twin (`use_absolute_paper_directory` picks which is primary in `process_file`) → row fields flow into `Docs.aadd(**kwargs)` as trusted metadata, suppressing LLM citation inference.
**Invariant:** The manifest is FAIL-OPEN at read time (any parse failure ⇒ `{}` + log, never a build abort) but STRICT at row-consumption time (`DocDetails(**entry)` raises on unknown/invalid fields). A missing header row therefore degrades every row silently to "infer with LLM" — pinned by test_getting_manifest expecting exactly one ERROR log.
**Probe:** `tests/test_agents.py::test_getting_manifest` (:238-260) — deleting the header line produces exactly one ERROR caplog record and no exception; `::test_get_directory_index_w_manifest` (:281-330) pins that `top_result.title == "Frederick Bates (Wikipedia article)"` comes from the manifest, not an LLM.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "paper-qa", query: "maybe_get_manifest fetch_kwargs_from_manifest finalize_manifest_file", limit: 10 });
// trace_path --function-name get_directory_index --direction outbound → maybe_get_manifest edge
```

## Verdict
Adopt the two-stage posture (fail-open catalog read + strict per-row model validation) for any bulk-import sidecar; adapt the DocDetails field set to your schema and keep the dual-key primary/fallback twin if your paths may be recorded in either form; omit the py<3.12 compatibility branch if you require ≥3.12 only. Coverage caveat: all cited paths `no_recorded_issue` + `metadata_match` at the pinned HEAD.
