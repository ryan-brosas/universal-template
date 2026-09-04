<!-- capsule-v2 -->
# Row-file schema gate — how do JSONL/JSON inputs get validated against a dataclass without drift?

**Source:** zep Apache-2.0 @ `7de18dfa`; Codebase Memory `ext-zep`. **Question:** How does rows_to_fields reject misspelled/missing/retired columns with actionable messages?

## _io.py
**Path/Symbol:** `ingestion/src/zep_ingest/_io.py:21` (`load_rows`), `:54` (`rows_to_fields`).
**Signature:** `load_rows(path) -> list[dict]` (JSONL, JSON array, or single object; .csv explicitly refused with a pointer to ingest_json_records); `rows_to_fields(rows, row_type, *, retired_fields=None) -> list[dict]`.
**Data Shape:** allowed = dataclass field names; required = fields with NO default; retired = former public names mapped to actionable errors.

### Decisive source
```python
# Unknown columns are rejected because silently dropping a misspelled public
# field can produce a valid-looking but semantically incomplete ingestion.
# Omitted required columns are rejected here too, so a chat export missing
# ``name`` or ``created_at`` names the field and the row rather than
# surfacing as a bare TypeError from the dataclass constructor.
unknown = sorted(set(row) - allowed)
if unknown:
    raise ConfigurationError(f"Row {index} has unknown field(s): {', '.join(unknown)}. "
                             f"Expected fields: {', '.join(sorted(allowed))}.")
...
for name in sorted(set(row) & retired.keys()):
    raise ConfigurationError(f"Row {index}: {retired[name]}")
```

**Flow:** empty file RAISES ("an empty file parses as zero JSONL rows, so without this the run succeeds having ingested nothing — usually a wrong path, not intent") → whole-text json.loads tried first, per-line fallback → non-dict/non-list refused → per-row retired→unknown→missing checks → validated dicts passed to the dataclass constructor which runs eager __post_init__ validation.
**Invariant:** Both allowed AND required sets are READ OFF THE DATACLASS ("so neither can drift from it") — adding a field to ThreadMessage automatically updates the row contract. Retired fields are checked BEFORE the generic unknown path so the message names the migration ("uuid cannot be supplied: Zep assigns node UUIDs …").
**Probe:** `grep -c 'def test' ingestion/tests/test_io.py` → ≥8 incl. empty-file and retired-field cases.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-zep", query: "rows_to_fields load_rows retired unknown required", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt dataclass-derived row schemas + retired-field migration messages + empty-file refusal; adapt file formats to your callers; omit CSV refusal if your schemas are flat.
