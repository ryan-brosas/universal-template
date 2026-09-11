<!-- capsule-v2 -->
# Entity-id coercion — where does a non-string scope ID get normalized so every operation sees the same key?

**Source:** mem0 MIT `main@001c2352`; Codebase Memory `mem0`. **Question:** how are user/agent/run IDs validated once and consistently across add/search/get_all/delete_all?

## Connected graph-selected seam
**Path/Symbol:** `mem0/memory/main.py`: `_validate_and_trim_entity_id` (:175-209), `_reject_top_level_entity_params` (:165-172), `ENTITY_PARAMS` frozenset (:135); applied in `_build_filters_and_metadata` (:372-374), `search` (:1445-1456), `get_all` (:1289-1300), `delete_all` (:1899-1901).
**Signature:** `_validate_and_trim_entity_id(value, name) -> Optional[str]`; raises `ValueError` on empty or whitespace-containing ids.
**Data Shape:** returns the stripped string, or None when input is None; int/other types coerced via `str()` at this single point.

### Decisive source
```python
# Callers commonly pass integer ids (e.g. a database primary key). Coerce
# to str at this single validation point so scoping stays consistent across
# add/search/get_all/delete_all instead of crashing on `.strip()`.
if not isinstance(value, str):
    value = str(value)
trimmed = value.strip()
if trimmed == "":
    raise ValueError(f"Invalid {name}: cannot be empty or whitespace-only. ...")
if any(c.isspace() for c in trimmed):
    raise ValueError(f"Invalid {name}: cannot contain whitespace. ...")
```

**Flow:** every entry point funnels its entity params through this one function BEFORE any store call; search/get_all additionally reject top-level entity kwargs (`_reject_top_level_entity_params`) forcing the `filters=` dict form, while add/delete_all accept them top-level — an intentional API asymmetry documented in `add()`'s docstring.
**Invariant:** coercion happens at exactly ONE chokepoint (per-call-site str() would let `" 42"` vs `42` diverge into two scopes); internal whitespace is rejected AFTER trimming so `"a b"` fails but `" a "` passes as `"a"`; None is legal (param absent), empty is not.
**Probe:** `tests/test_main.py::test_delete_all_rejects_whitespace_only_user_id` (:435), `::test_delete_all_trims_user_id_before_list` (:445), `::test_delete_all_coerces_integer_user_id_before_list` (:460).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mem0", query: "_validate_and_trim_entity_id coerce integer reject top level entity params", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt single-chokepoint validation with trim-then-whitespace-check ordering; adapt error messages; the add-vs-search kwargs asymmetry must be preserved or filters silently stop scoping.
