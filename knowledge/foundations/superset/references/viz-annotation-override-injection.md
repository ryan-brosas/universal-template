<!-- capsule-v2 -->
# viz-annotation-override-injection — How do you render a chart-as-annotation-layer with per-layer overrides while keeping the requesting user's security context?

**Source:** Apache Superset Apache-2.0 `master@9f505eb0cbbc39b78f512765d82fd63cf5ad70e6`; Codebase Memory `superset`. **Question:** A chart can embed other charts as annotation layers (sourceType `line`/`table`) with per-layer overrides — how do the overrides reach the nested queries, and who is authorized for the nested execution?

## Viz annotation layer execution
**Path/Symbol:** `superset/common/query_context_processor.py` — `QueryContextProcessor.get_viz_annotation_data` (:709-754), dispatched from `get_annotation_data` (:649-660) for layers with `sourceType in ("line", "table")`.
**Signature:** `get_viz_annotation_data(annotation_layer: dict[str, Any], force: bool) -> dict[str, Any]` (staticmethod).
**Data Shape:** layer dict `{name, value: chart_id, overrides?: {time_grain_sqla?, time_range?}}`; output `{"records": <nested query rows>}`; all failures normalized to `QueryObjectValidationError`.

### Decisive source
```python
if not (chart := ChartDAO.find_by_id(annotation_layer["value"])):
    raise QueryObjectValidationError(...)
...
if overrides := annotation_layer.get("overrides"):
    if time_grain_sqla := overrides.get("time_grain_sqla"):
        for query_object in query_context.queries:
            query_object.extras["time_grain_sqla"] = time_grain_sqla

    if time_range := overrides.get("time_range"):
        from_dttm, to_dttm = get_since_until_from_time_range(time_range)
        for query_object in query_context.queries:
            query_object.from_dttm = from_dttm
            query_object.to_dttm = to_dttm

query_context.force = force
command = ChartDataCommand(query_context)
command.validate()
payload = command.run()
return {"records": payload["queries"][0]["data"]}
except SupersetException as ex:
    raise QueryObjectValidationError(error_msg_from_exception(ex)) from ex
```

**Flow:** resolve the referenced chart by id (missing ⇒ typed error naming chart id + layer name) → rebuild its stored query context (missing ⇒ typed error) → apply overrides in fixed order: `time_grain_sqla` into every query's `extras`, then `time_range` into `from_dttm`/`to_dttm` via the shared since/until resolver → propagate the OUTER request's `force` flag into the nested context → re-run `ChartDataCommand.validate()` (i.e. `raise_for_access`) on the nested context under the CURRENT user before `run()` → return only the first query's records; every `SupersetException` is wrapped into a `QueryObjectValidationError` with the exception's error message.
**Invariant:** The nested execution must be re-authorized under the requesting user — the stored chart's own permissions are not inherited; overrides mutate the reconstructed context in place before validation so the security check sees the final shape; `force` propagation means "refresh the outer chart" also refreshes annotation data; no nested failure may escape as a raw `SupersetException` type the caller does not handle.
**Probe:** No direct unit test exists for `get_viz_annotation_data` (coverage caveat — verified by grep across tests/unit_tests this pass). Integration: `tests/integration_tests/charts/data/api_tests.py:995-1032` pins the surrounding dispatch (`get_annotation_data`) end-to-end: formula excluded, interval + event returned, 200 status.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "superset", query: "get_viz_annotation_data overrides time_grain_sqla time_range force validate", limit: 10 });
```

## Verdict
Adopt override-then-validate ordering (mutate the reconstructed context first, then authorize the final shape), force-flag propagation into nested executions, and single-exception-type normalization at the seam boundary; adapt the chart-store lookup and since/until resolver to your host; omit Superset's ChartDAO/QueryContext storage format. Coverage caveat: no direct unit test pins the override branches — the invariant rests on the read source plus the integration dispatch test; MCP disconnected this pass — Retrieve is a documented target.
