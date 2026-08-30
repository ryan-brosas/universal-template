<!-- capsule-v2 -->
# Temporal-usage detectors — how do you recognize "the user is doing something time-shaped" from raw queries, filters, and metadata?

**Source:** mem0 MIT `main@8d5b7865`; Codebase Memory `mnt-hdd-utopia-inspo-memory-mem0`. **Question:** what regex/structural rules decide that a query string, filter dict, or metadata blob contains a temporal intent — and which traps (epoch ranges, relative phrases, range operators on non-date keys) must a port reproduce exactly to avoid false positives/negatives?

## Connected graph-selected seam
**Path/Symbol:** `mem0/memory/notices.py`: `_ISO_DATE_RE` (:51-53), `_RELATIVE_TIME_RE` (:54-64), `_RANGE_OPERATORS = {gt,gte,lt,lte}` (:65), `detect_temporal_usage_from_metadata` (:821-832), `detect_temporal_usage_from_search` (:835-850), `_walk_mapping` (:1510-1518), `_is_temporal_key` (:1521-1542), `_looks_temporal_value` (:1545-1554), `_has_temporal_filter` (:1557-1582). Direct tests `tests/memory/test_notices.py` :600-663 (query/filter matrices incl. negative `"favorite drink"`).
**Signature:** `detect_temporal_usage_from_search(query: Any, filters: Optional[Dict]) -> Optional[Tuple[str,str]]`; `detect_temporal_usage_from_metadata(metadata) -> Optional[Tuple[str,str]]`; helpers return `(source, reason)` pairs like `("query","relative_phrase")`, `("filter","date_range_filter")`, `("metadata","date_like_metadata")`.
**Data Shape:** inputs are arbitrary user JSON; output is a 2-tuple or None. Key classifier vocabulary: exact keys {date,time,timestamp,datetime,event_date,reference_date,created_at,updated_at,started_at,ended_at,expires_at} + suffix rules (`_date`/`_time`/`_at`) + substring "timestamp"; epoch window ints `[946684800, 4102444800]` seconds or ×1000 ms.

### Decisive source
```python
_RELATIVE_TIME_RE = re.compile(
    r"\b(today|yesterday|tomorrow|"
    r"last\s+(?:night|week|month|year)|this\s+(?:week|month|year)|next\s+(?:week|month|year)|"
    r"(?:past|last)\s+\d+\s+(?:day|days|week|weeks|month|months|year|years)|"
    r"(?:since|before|after|until)\s+(?:today|yesterday|tomorrow|\d{4}-\d{2}-\d{2}|last\s+(?:week|month|year))"
    r")\b", re.IGNORECASE)

def _is_temporal_key(key):                       # suffixes make ANY *_date/*_time/*_at key temporal
    k = str(key).lower()
    return (k in exact_keys or k.endswith("_date") or k.endswith("_time")
            or k.endswith("_at") or "timestamp" in k)

def _looks_temporal_value(value, allow_epoch):
    if isinstance(value, datetime) or isinstance(value, date): return True
    if isinstance(value, str):
        return bool(_ISO_DATE_RE.search(value) or _RELATIVE_TIME_RE.search(value))
    if allow_epoch and isinstance(value, (int, float)) and not isinstance(value, bool):
        return 946684800 <= value <= 4102444800 or 946684800000 <= value <= 4102444800000
    return False

def _has_temporal_filter(filters):
    for key, value in filters.items():
        if key in {"AND","OR","NOT","$and","$or","$not"}:          # recurse into BOTH dialects
            ...any recursion...
            continue                                               # ← logical keys never fall through
        temporal_key = _is_temporal_key(key)
        if isinstance(value, dict):
            range_values = [item for op, item in value.items() if op in _RANGE_OPERATORS]
            if range_values and (temporal_key or
                any(_looks_temporal_value(item, allow_epoch=temporal_key) for item in range_values)):
                return True                                        # numeric gte ONLY counts on a temporal key
```

**Flow:** query path checks `_RELATIVE_TIME_RE` FIRST then `_ISO_DATE_RE` (so "what happened last week?" wins before any date scan) → filter path walks top-level entries, recursing through AND/OR/NOT in both upper and `$lower` dialects → a `{op: value}` dict triggers the range-operator rule where bare numerics count only when the KEY is already temporal (`allow_epoch=temporal_key` coupling) → metadata path deep-walks every mapping/list/set via `_walk_mapping` and requires BOTH a temporal key AND a temporal-looking value.
**Invariant:** (1) epoch detection is gated by `not isinstance(value, bool)` — Python bools are ints and `True` would otherwise read as epoch 1e9-adjacent; (2) logical-operator keys (`AND/$and/...`) are consumed by the `continue` and never evaluated as data keys — dropping it makes `{"NOT": {...}}` a false positive via the `endswith("_at")`-style suffixes? no — via the dict branch misfire; (3) range operators without a date-like VALUE on a non-temporal key (e.g. `score.gte=0.5`) return None — test-pinned; (4) every detector is wrapped in try/except returning None: detection failure degrades to silence, never raises into add/search.
**Probe:** `tests/memory/test_notices.py::detect_temporal_usage_from_search returns ("query","relative_phrase")` (:614), `("query","date_like_query")` for "notes from 2025-04-09" (:618), None for "favorite drink" (:622), `("filter","date_range_filter")` for date-keyed gt/gte filters (:652), and the `{score:{gte:0.5}}→None` negative (:656).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-memory-mem0", query: "detect_temporal_usage_from_search _is_temporal_key", limit: 10, fields: ["signature", "name", "file"] });
```
(resolved live pre-write: notices.py 835-850 / 1521-1542; TS twin mirrors at mem0-ts/src/oss/src/utils/notices.ts 714-741/870-890)

## Verdict
Adopt the two-regex vocabulary and the operator-vs-data-key split verbatim — they encode which user phrasings count as time-intent; adapt the key vocabularies to your domain's field names; omit the metadata deep-walk if you only classify explicit search inputs (keep the try/except-None envelope either way).
