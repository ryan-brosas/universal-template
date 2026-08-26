<!-- capsule-v2 -->
# annotation-cache-context-binding — How does a shared cache entry stay correct when annotation data is per-user and RLS-bound?

**Source:** Apache Superset Apache-2.0 `master@9f505eb0cbbc39b78f512765d82fd63cf5ad70e6`; Codebase Memory `superset`. **Question:** When annotation payloads are cached on the SAME entry as the dataframe, what must the cache key additionally bind?

## query_cache_key + _annotation_cache_context
**Path/Symbol:** `superset/common/query_context_processor.py:267-290` (`query_cache_key`) and `:292-316` (`_annotation_cache_context`).
**Signature:** `def query_cache_key(self, query_obj: QueryObject, **kwargs: Any) -> str | None`; `def _annotation_cache_context(self, query_obj: QueryObject) -> dict[str, Any]`
**Data Shape:** context dict `{"user_id": <int|None>, "source_rls": {str(layer_value): list[str] | None}}` injected as kwarg `annotation_context` into `QueryObject.cache_key`.

### Decisive source
```python
# Annotation data is cached on the same entry as the dataframe, so the
# key must also bind the annotation sources' security context.
if query_obj and query_obj.annotation_layers:
    kwargs["annotation_context"] = self._annotation_cache_context(query_obj)

cache_key = (
    query_obj.cache_key(
        datasource=datasource.uid,
        extra_cache_keys=extra_cache_keys,
        rls=security_manager.get_rls_cache_key(datasource),
        changed_on=datasource.changed_on,
        **kwargs,
    )
    if query_obj
    else None
)
```

```python
for layer in query_obj.annotation_layers:
    if layer.get("sourceType") not in ("line", "table"):
        continue
    layer_value = layer.get("value")
    chart = ChartDAO.find_by_id(layer_value) if layer_value is not None else None
    annotation_datasource = chart.datasource if chart else None
    source_rls[str(layer.get("value"))] = (
        security_manager.get_rls_cache_key(annotation_datasource)
        if annotation_datasource else None
    )
return {"user_id": get_user_id(), "source_rls": source_rls}
```

**Flow:** only chart-backed layers (`sourceType ∈ {line, table}`) contribute; NATIVE layers are skipped here (they get a permission check + DAO read in `get_native_annotation_data` instead). For each such layer the referenced chart's *own datasource* RLS cache key is resolved (not the host chart's). The whole context rides the key as one kwarg, so any user/RLS change splits entries.
**Invariant:** Two users (or two RLS states on an annotated source) must never share one dataframe+annotation cache entry; conversely identical context must hash identically.
**Probe:** `tests/unit_tests/common/test_query_context_processor.py:102-118` (`test_query_cache_key_binds_annotation_data_to_requesting_user`) patches `get_user_id` to 1 then 2 and asserts the two `annotation_context` kwargs differ.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "superset", query: "annotation_context cache key user rls", limit: 10 });
```

## Verdict
Adopt co-locating derived data with its host entry ONLY while binding every security dimension of that derived data into the key; adapt `ChartDAO`/`security_manager` lookups to your access layer; omit NATIVE-layer handling if you store annotations differently. Coverage: both ranges read directly at pin; direct test read :102-118; files `no_recorded_issue`.
