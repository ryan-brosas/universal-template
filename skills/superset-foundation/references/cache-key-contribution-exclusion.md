<!-- capsule-v2 -->
# cache-key-contribution-exclusion — Which request-varying values must be stripped from a query cache key, and which normalizations keep it stable?

**Source:** Apache Superset Apache-2.0 `master@9f505eb0cbbc39b78f512765d82fd63cf5ad70e6`; Codebase Memory `superset`. **Question:** How does `QueryObject.cache_key` hash the same logical query identically on different workers despite runtime-mutated state and hash-randomized sets?

## QueryObject.cache_key
**Path/Symbol:** `superset/common/query_object.py:518-614`.
**Signature:** `def cache_key(self, **extra: Any) -> str` → `hash_from_dict(cache_dict, default=json_int_dttm_ser, ignore_nan=True)`.
**Data Shape:** `cache_dict = dict(self.to_dict()) + extra`; post_processing is a list of `{operation, options}` dicts.

### Decisive source (runtime value exclusion)
```python
if self.post_processing:
    # Exclude contribution_totals from post_processing as it's computed at
    # runtime and varies per request, which would cause cache key mismatches
    post_processing_for_cache = []
    for pp in self.post_processing:
        pp_copy = dict(pp)
        if pp_copy.get("operation") == "contribution" and "options" in pp_copy:
            options = dict(pp_copy["options"])
            # Remove contribution_totals as it's dynamically calculated
            options.pop("contribution_totals", None)
            pp_copy["options"] = options
        post_processing_for_cache.append(pp_copy)
    cache_dict["post_processing"] = post_processing_for_cache
```

### Decisive source (set-order normalization + resolved-bound removal)
```python
cache_dict["extra_cache_keys"] = sorted(
    cache_dict["extra_cache_keys"],
    key=lambda value: (type(value).__name__, str(value)),
)
...
for k in ["from_dttm", "to_dttm"]:
    del cache_dict[k]
```

**Flow:** start from `to_dict()` + extras → sort `extra_cache_keys` (opaque Jinja `url_param()` values; sort by `(type name, str)` so `1` vs `"1"` still order deterministically instead of falling back to per-process set-iteration order — `hash_from_dict` sorts dict keys but NOT list values) → drop the `apply_fetch_values_predicate` key unless enabled → override `datasource` to uid, add `result_type`, raw `time_range`, normalized post_processing (totals popped), `time_offsets` → delete resolved `from_dttm/to_dttm` (the *inputs* like `time_range` remain, keeping relative ranges shareable) → project annotation layers onto a ten-field whitelist before hashing → conditionally add an impersonation key via `add_impersonation_cache_key_if_needed` (AttributeError-swallowed when no database). Debug logging of the key is emitted only at DEBUG level.
**Invariant:** Only one op name (`contribution`) has an option excluded — every other option change must split the key; resolved datetime bounds never enter, their source inputs do.
**Probe:** three direct tests pin all three faces — `tests/unit_tests/common/test_query_context_processor.py:1727` (`test_cache_key_excludes_contribution_totals`: keys equal with/without totals), `:1785` (`..._preserves_other_post_processing_options`: different `rename_columns` ⇒ different key), `:1836` (`..._non_contribution_post_processing_unchanged`: pivot aggregate change splits key).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "superset", query: "QueryObject cache_key extra_cache_keys contribution_totals", limit: 10 });
```

## Verdict
Adopt exclude-runtime-values + normalize-set-ordering + strip-resolved-bounds as the three key-stability rules; adapt the whitelist fields to your layer schema; omit impersonation keying if your DBs don't impersonate. Coverage: whole method read at pin; three direct tests read; file `no_recorded_issue`.
