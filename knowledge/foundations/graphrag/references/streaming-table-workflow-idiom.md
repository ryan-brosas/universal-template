<!-- capsule-v2 -->
# Streaming-table workflow idiom — async table handles, sample-rows-of-5, and the same-file read/write trap

**Source:** graphrag MIT `main@60668ba946ccfd5cb784c578efedff86798a2c35`; Codebase Memory project `graphrag`. **Question:** How do workflows process datasets larger than memory without DataFrames, and what makes opening the SAME table for read and write safe?

## Key facts
**Path/Symbol:** `graphrag/index/workflows/create_base_text_units.py` (`create_base_text_units` :56-124 streaming chunker; `chunk_document` :127-160); `create_final_documents.py:51-73` (reverse-lookup map + stream-enrich); `create_final_text_units.py` (nullcontext stand-in :36-42, SAME-FILE comment :44-46, `_build_multi_ref_map` :117-127); `finalize_graph.py` (`_build_degree_map` streaming Counter :98-125).
**Signature:** tables are opened as `table_provider.open(name, truncate=False?, transformer=row_fn?)` inside ONE `async with (...)` tuple-block; rows arrive via `async for row in table`; writes via `await table.write(row)`; every workflow returns ≤5 `sample_rows` for logging.
**Data Shape:** Row dicts with FINAL_COLUMNS projection at write time (`out = {c: fields[c] for c in TEXT_UNITS_FINAL_COLUMNS}`); transformers parse stringified list fields (`text_unit_ids`) into Python lists BEFORE row iteration.

### Decisive source
```python
# create_final_text_units.py :36-46 — two non-obvious moves in one block:
cov_ctx = (
    context.output_table_provider.open("covariates")
    if has_covariates
    else nullcontext()          # optional table = nullcontext so ONE with-block serves both cases
)
# The read and write handles for text_units share the same file.
# CSVTable writes to a temp file and moves it on close(), so
# reads from the original remain safe throughout.            # ← why read+write on one path is legal
```
```python
# finalize_graph.py :117-124 — degree map WITHOUT materializing a DataFrame;
# undirected pair normalization + on-the-fly dedup match compute_degree semantics
seen: set[tuple[str, str]] = set()
degree: Counter[str] = set()
async for row in relationships_table:
    lo, hi = sorted((row["source"], row["target"]))
    if (lo, hi) not in seen:
        seen.add((lo, hi)); degree[lo] += 1; degree[hi] += 1
```
**Flow:** open all needed handles up front (readers usually `truncate=False`, writers fresh) → build small in-memory lookup maps by streaming once → stream the primary table, enrich each row from maps, project to FINAL_COLUMNS, write → collect first 5 rows as samples.
**Invariant:** maps must be built BEFORE the enrichment pass (single pass over each input); sample_rows capped at 5 is a logging contract, not data output; same-file dual handles are ONLY safe because CSVTable close() does temp-file+rename — a porter using direct in-place writers breaks this; `truncate=False` distinguishes re-reads from fresh outputs.
**Probe:** `tests/unit/indexing/test_finalize_graph.py` (:129/:138 duplicate + reversed-duplicate dedup through the degree ladder, :172 enriches-with-degree, :185 missing-degree→0, :253 returns-sample-rows-up-to-five); `tests/unit/indexing/test_create_communities.py` streams via an in-memory Table collecting writes (:27 fixture).
**Retrieve:** `await mcp.codebase_memory.search_graph({ project: "graphrag", query: "async for row table write sample_rows transformer truncate", limit: 10 })`

## Verdict
Adopt streaming handles + prebuilt reverse-lookup maps + 5-row samples + FINAL_COLUMNS projection; adapt table backend. Do NOT port the same-file dual-handle pattern without a temp-file-and-rename writer.
