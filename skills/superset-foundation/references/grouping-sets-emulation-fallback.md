<!-- capsule-v2 -->
# grouping-sets-emulation-fallback — How do you produce native-GROUPING-SETS-shaped results on engines that don't support them?

**Source:** Apache Superset Apache-2.0 `master@9f505eb0cbbc39b78f512765d82fd63cf5ad70e6`; Codebase Memory `superset`. **Question:** When the engine lacks native GROUPING SETS, how are rollup levels executed and recombined without diverging from the native shape?

## _supports_grouping_sets / _grouping_sets_fallback
**Path/Symbol:** `superset/common/query_context_processor.py:318-401` (`get_query_result` dispatch :318-334, `_supports_grouping_sets` :336-340, `_grouping_sets_fallback` :342-401).
**Signature:** `def get_query_result(self, query_object: QueryObject) -> QueryResult`; `def _grouping_sets_fallback(self, query_object: QueryObject) -> QueryResult`
**Data Shape:** `query_object.grouping_sets: list[list[str]]` (rollup levels as column-label lists); per-level marker column `grouping_marker_label(label)` ∈ {0,1} appended to each frame.

### Decisive source
```python
# Zero it here and apply it once after concatenation instead.
sub_query.row_limit = None
sub_query.row_offset = 0
result = self._qc_datasource.get_query_result(sub_query)
level_df = result.df.copy()
for label in all_labels:
    level_df[grouping_marker_label(label)] = (
        0 if label in level_labels else 1
    )
frames.append(level_df)
...
result.df = pd.concat(frames, ignore_index=True) if frames else result.df
if query_object.row_offset:
    result.df = result.df.iloc[query_object.row_offset :].reset_index(drop=True)
```

**Flow:** dispatch — if `grouping_sets` requested but `db_engine_spec.supports_grouping_sets` is falsy, emulate; else single native query. Emulation: for each rollup level, copy the query object, restrict `columns` to that level's labels (via a shared label→column map built with the SAME `get_column_name` derivation as the native path), clear its `grouping_sets`, run it sequentially, tag every row with 0/1 grouping markers per original label (0 = in this level, 1 = aggregated away). Concatenate all levels; apply `row_offset` exactly once over the combined frame.
**Invariant:** The docstring pins two divergence traps the emulation must avoid to match native shape: (a) applying `row_limit` per level would truncate subtotal/grand-total rows (native path never limits grouping-set queries — see `use_grouping_sets` check in `models/helpers.py`), so per-level `row_limit=None`; (b) applying `row_offset` per level would offset once-per-level and can silently drop low-row-count levels entirely (e.g. the single grand-total row), so per-level `row_offset=0` and one post-concat slice. Also documented honestly: level count is bounded only by dimensionality (powerset worst case) with **no cap** on sequential queries.
**Probe:** `tests/unit_tests/common/test_query_context_processor.py:2248` (`test_grouping_sets_fallback_applies_row_offset_once_globally`) and `:2194-2245` (`test_grouping_sets_fallback_handles_adhoc_and_physical_columns` — pins that `label_to_column` must derive from the SAME labels as the level subqueries, else an adhoc column ahead of a physical one silently drops from `grouping_sets`; captured per-level columns assert `[adhoc, "state"]`, `[adhoc]`, `[]`). Marker vocabulary lives in `superset/common/grouping_sets.py:44-46` (`grouping_marker_label`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "superset", query: "grouping sets fallback row_offset marker", limit: 10 });
```

## Verdict
Adopt per-level un-limited execution + marker tagging + single post-hoc offset as the emulation contract; adapt marker-column naming and label derivation to your engine spec layer; omit the fallback entirely when you require native GROUPING SETS support. Coverage: whole range read at pin; two dedicated unit tests read directly (:2194-2245, :2248-2296); file `no_recorded_issue`.
