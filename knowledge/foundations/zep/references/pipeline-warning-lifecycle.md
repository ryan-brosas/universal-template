<!-- capsule-v2 -->
# Pipeline warning lifecycle — how do warnings from reused components get collected without duplicates or loss?

**Source:** zep Apache-2.0 @ `7de18dfa`; Codebase Memory `ext-zep`. **Question:** How does Pipeline collect per-component warnings across a preview() AND a run() on the same objects?

## Warning baseline + flush + counter
**Path/Symbol:** `ingestion/src/zep_ingest/pipeline.py:48-56` (`_MissingTimestampCounter`), `:108` (`_stream`), `:117` (`_warning_baseline`), `:124` (`_collect_warnings`), `:143` (`preview`), `:164` (`run`).
**Signature:** `_warning_baseline() -> dict[int, int]` keyed by `id(source)` → `len(source.warnings)`; `_collect_warnings` slices `source_warnings[baseline.get(id(source), 0):]`.
**Data Shape:** Sources = `(loader, *transforms)`; guard (LimitGuard) and counter warnings are appended fresh each pass; preview appends a sample-scope caveat string when `limit is not None`.

### Decisive source
```python
# pipeline.py _warning_baseline docstring — the reason for the id-keyed delta
# The loader and transforms may be reused across preview() and run();
# collect only the warnings each pass adds, not the accumulated history.
return {
    id(source): len(getattr(source, "warnings", [])) for source in self._warning_sources()
}
```

**Flow:** pass start → snapshot baseline lengths → run stream (counter.wrap wraps AFTER guard so missing-timestamp counting sees post-split episodes) → flush each source's `flush_warnings()` if present → extend result.warnings with per-source deltas + guard.warnings + counter.warnings (+ preview caveat).
**Invariant:** The SAME loader/transform instances are reusable across passes, so collection must be delta-based (`id()` keys, sliced from baseline) or a preview+run pair double-reports every warning. A limited preview leaves generators suspended mid-yield, hence mandatory flush before reading. `preview(limit=None)` is the exhaustive preflight; sample-scoped warnings always carry the caveat text.
**Probe:** `grep -c 'baseline.get(id(source)' ingestion/src/zep_ingest/pipeline.py` → 1; direct tests `ingestion/tests/test_pipeline.py` (30 tests).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-zep", query: "Pipeline warning baseline preview run", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt id-keyed baseline-delta warning collection for any reusable pipeline component; adapt the counter wrapper position (post-guard) to your stream order; omit Zep's specific missing-timestamp warning wording.
