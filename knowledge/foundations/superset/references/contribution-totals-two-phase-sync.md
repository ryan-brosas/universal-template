<!-- capsule-v2 -->
# contribution-totals-two-phase-sync — How do contribution charts get their totals without breaking worker↔fetch cache-key parity?

**Source:** Apache Superset Apache-2.0 `master@9f505eb0cbbc39b78f512765d82fd63cf5ad70e6`; Codebase Memory `superset`. **Question:** Where are runtime-computed totals injected, and what must be re-synced afterward so cache keys still match across processes?

## _prepare_contribution_totals / ensure_totals_available / get_payload_result sync
**Path/Symbol:** `superset/common/query_context_processor.py:432-459` (`_prepare_contribution_totals`), `:461-486` (`ensure_totals_available`), `:509-528` (sync block in `get_payload_result`).
**Signature:** `_prepare_contribution_totals(self) -> tuple[list[int], int | None]`; `ensure_totals_available(self, queries_needing_totals=None, totals_idx=None) -> None`
**Data Shape:** totals query discriminator: `not query.columns and query.metrics and not query.post_processing`; totals dict `{column: df[col].sum()}` for numeric-kind columns only (`dtype.kind in "biufc"`).

### Decisive source
```python
if queries_needing_totals and totals_idx is not None:
    totals_query = self._query_context.queries[totals_idx]
    totals_query.row_limit = None          # totals must never be truncated
...
totals = {col: df[col].sum() for col in df.columns if df[col].dtype.kind in "biufc"}
for idx in queries_needing_totals:
    ...
    for pp in query.post_processing:
        if pp.get("operation") == "contribution":
            pp["options"]["contribution_totals"] = totals
```

```python
if not force_cached:
    self.ensure_totals_available(queries_needing_totals, totals_idx)
    # Update cache_values to reflect modifications made by ensure_totals_available()
    self._query_context.cache_values["queries"] = [
        {**cached_query, **query.to_dict()}
        for cached_query, query in zip(
            self._query_context.cache_values["queries"],
            self._query_context.queries,
            strict=True,
        )
    ]
```

**Flow:** (1) classify each context query — does it carry a `contribution` post-processing op, and which one is the implicit totals query; (2) un-cap the totals query's `row_limit` so subtotals/grand totals can't be truncated by the user's chart row limit; (3) execute the totals query once via `QueryContext.get_query_result`, sum numeric columns, mutate each contribution op's `options["contribution_totals"]` **in place**; (4) re-derive `cache_values["queries"]` by merging the original cached dicts with fresh `to_dict()` output (original keys preserved, mutated values win) so the context-level cache key computed from `cache_values` equals the key a worker would compute from the mutated live objects. The whole injection is skipped when `force_cached=True` (recalculating totals from cached results is both wasteful and wrong).
**Invariant:** After phase 2, `cache_values` and the live QueryObjects describe the SAME query state; per-request totals themselves must never enter a key (see `cache-key-contribution-exclusion`).
**Probe:** `tests/unit_tests/common/test_query_context_processor.py:1352-1515` (`test_ensure_totals_available_updates_cache_values`) asserts `updated_cache_queries[1]["row_limit"] is None` and `contribution_totals` present with exact mocked sums; `:1596-1724` pins cache-value sync after injection.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "superset", query: "ensure_totals_available contribution_totals prepare", limit: 10 });
```

## Verdict
Adopt the two-phase protocol (classify+un-cap → inject → re-sync serializable state); adapt the totals-query discriminator and numeric-column fold to your op vocabulary; omit the `force_cached` skip only if you have no async/cache-only path. Coverage: all three ranges read directly at pin; two direct tests read; file `no_recorded_issue`.
