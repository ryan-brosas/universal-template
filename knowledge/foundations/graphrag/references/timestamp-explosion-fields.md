<!-- capsule-v2 -->
# Timestamp explosion — how do you make ISO timestamps filterable by vector stores that only support scalar field predicates?

**Source:** graphrag MIT `main@6dad6d2b059589624035714d8dcfde94ecc0a5fb`; Codebase Memory `graphrag`. **Question:** how does a flat metadata schema answer "docs from Monday" or "Q3" queries without temporal SQL, and what does the field-registration lifecycle look like?

## explode_timestamp + auto-registration in VectorStore.__init__
**Path/Symbol:** `packages/graphrag-vectors/graphrag_vectors/timestamp.py` (`_SUFFIXES` :22-31, `_timestamp_fields_for` :32-34, `TIMESTAMP_FIELDS` :37-39, `explode_timestamp` :44-95) + `vector_store.py` (`__init__` date-field detection :82-90, `_prepare_document` :97-120, `_prepare_update` :122-133).
**Signature:** `explode_timestamp(iso_timestamp: str | None, prefix: str = "create_date") -> dict[str, str | int]`; `TimestampExploder = Callable[[str, str], dict[str, str | int]]` (injectable, default `explode_timestamp`).
**Data Shape:** 7 component fields per prefix: `{prefix}_year:int, _month:int(1-12), _month_name:str("March"), _day:int, _day_of_week:str("Friday"), _hour:int(0-23), _quarter:int(1-4)`; built-in prefixes `create_date`/`update_date` = 14 auto-registered fields.

### Decisive source
```python
# timestamp.py:94 — quarter is integer floor-division math on the MONTH,
# not a calendar quarter of any fiscal system:
"{prefix}_quarter": (dt.month - 1) // 3 + 1,
```
```python
# vector_store.py:82-87 — user "date"-typed fields are DEMOTED to str and
# their exploded components appended; the raw value stays for exact reads
self.date_fields = [n for n, ftype in self.fields.items() if ftype == "date"]
for name in self.date_fields:
    self.fields[name] = "str"
    self.fields.update(_timestamp_fields_for(name))
# :106-109 insert path — create_date DEFAULTS TO NOW (documents are never
# without a create stamp); update_date exploded ONLY if present
if not document.create_date:
    document.create_date = self._now_iso()
document.data.update(self.timestamp_exploder(document.create_date, "create_date"))
```

**Flow:** declare fields config → `VectorStore.__init__` detects `ftype == "date"`, demotes to str, registers `{name}_{suffix}` components + always merges TIMESTAMP_FIELDS → at `load_documents` time `_prepare_document` stamps missing create_date with UTC-now ISO, explodes create/update/user-date values into `document.data` → backend extracts declared fields per row → queries filter on components via FilterExpr.
**Invariant:** explosion happens at WRITE time into the data dict (schema must reserve the 14+7k columns BEFORE load; adding a date field after an index exists requires re-index); empty/None timestamps explode to `{}` (no partial rows); `_now_iso` is timezone-aware UTC — naive local time would skew day_of_week/hour filters.
**Probe:** `tests/unit/vector_stores/test_timestamp.py` — `test_quarter` parametrized across all 12 months (:52-71), `test_total_count` pins `len(TIMESTAMP_FIELDS) == 14` (:110-112), `test_empty_string_returns_empty`/`test_none_returns_empty` (:40-46). `$VENV_ROOT/grag-lane-venv/bin/python -m pytest tests/unit/vector_stores/test_timestamp.py -q` → 9 passed @pin.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "graphrag", query: "explode timestamp quarter fields filterable components", limit: 10, fields: ["signature", "name", "file"] });
```
Live-resolved rank#1 `timestamp.explode_timestamp` :44-95.

## Verdict
Adopt write-time component explosion + now-defaulting create stamps + injectable exploder signature; adapt suffix set/locale month names to host; omit Azure-specific index mapping. No coverage caveat.
