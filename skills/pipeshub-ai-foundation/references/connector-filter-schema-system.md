<!-- capsule-v2 -->
# Filter schema system — how do UI-configured sync/indexing filters become validated runtime predicates with legacy-config tolerance?

**Source:** PipesHub AI Apache-2.0 `main@c28d1336`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-pipeshub-ai`. **Question:** Porting "let users filter what gets synced/indexed" needs a schema (UI) AND a parser (runtime) — how does this design keep them from drifting?

## Typed FilterFields + pydantic Filter with dual validators
**Path/Symbol:** `backend/python/app/connectors/core/registry/filters.py:` (1,054L) — `FilterType` 6 types (:36-46), `FilterCategory` SYNC-vs-INDEXING (:49-53), `FilterOperator` flat strings + per-type enums (:110-215), `TYPE_OPERATORS` map, `SyncFilterKey`/`IndexingFilterKey` canonical key enums (:230-330), `FilterField.to_schema_dict()` (UI schema), `Filter` model :491+ with `mode='before'` coercion validator and `validate_filter` after-validator (:612-700), `FilterCollection.get/get_value/is_enabled` (:805+).
**Signature:** `Filter(key, value, type, operator)`; datetime values normalize to `(start_epoch_ms | None, end_epoch_ms | None)` tuples (`MAX_DATETIME_TUPLE_LENGTH = 2`).
**Data Shape:** Config JSON: `{key, value, type, operator}`; LIST/MULTISELECT values always string-id arrays; MULTISELECT carries `{id,label}` options via `FilterOption` for UI.

### Decisive source
```python
# before-validator: tolerate every historical storage shape
if isinstance(value, str):                      # legacy single id stored bare
    data['value'] = [value.strip()] if value.strip() else []
elif isinstance(value, list):                   # new {id,label} objects → extract ids
    extracted_ids = [item['id'] if isinstance(item, dict) and 'id' in item else str(item)
                     for item in value]
# after-validator: operator must belong to the type's fixed vocabulary
valid_operators = TYPE_OPERATORS.get(self.type, [])
if operator_value not in valid_operators:
    raise ValueError(f"Invalid operator '{operator_value}' for type '{self.type.value}'. ...")
```

**Flow:** connector declares `FilterField`s at build time (category routes to filters.sync vs filters.indexing schema) → frontend renders schema → saved config parsed into `Filter` models: shape-coercion FIRST (dict→tuple datetimes, string→list, {id,label}→id) then vocabulary/type validation raising actionable ValueErrors listing valid operators → connectors consume via `FilterCollection.get_value(SyncFilterKey.FOLDERS)` / `is_enabled(IndexingFilterKey.ENABLE_MANUAL_SYNC, default=True)`.
**Invariant:** Operators are CLOSED per type (datetime gets only last_N_days/is_after/is_before/is_between) — the type-operators map is the single arbiter for both UI rendering and runtime validation, so they cannot diverge. INDEXING-category boolean record-type filters (pages/issues/emails...) are evaluated AFTER fetch; SYNC filters change WHAT is fetched.
**Probe:** `grep -c 'MAX_DATETIME_TUPLE_LENGTH = 2' app/connectors/core/registry/filters.py` → `1`; suite `tests/unit/connectors/core/test_filters.py` (129 tests) GREEN in battery.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-pipeshub-ai", query: "FilterCollection get_value SyncFilterKey IndexingFilterKey", limit: 3 });
```
**Verdict:** Adopt two-category split + closed operator vocabularies + coerce-then-validate pipeline; adapt key enums to hosted sources.
