<!-- capsule-v2 -->
# Qdrant filter translation — how do universal operators become native conditions, and which two traps wait in the $or/$not keys?

**Source:** mem0 MIT `main@001c2352`; Codebase Memory `mem0`. **Question:** how is the platform filter dialect compiled into a backend-native filter, and what must not be lost in translation?

## Connected graph-selected seam
**Path/Symbol:** `mem0/vector_stores/qdrant.py`: `_build_field_condition` (:265-337), `_create_filter` (:339-413), `_is_datetime_range` (:258-263); producer side `Memory._process_metadata_filters` (`main.py` :1524-1599) renames OR→`$or`, NOT→`$not`.
**Signature:** `_build_field_condition(key, value) -> Optional[FieldCondition]`; `_create_filter(filters) -> Optional[Filter]` (must/should/must_not lanes).
**Data Shape:** universal ops: eq/ne/gt/gte/lt/lte/in/nin/contains/icontains + AND/OR/NOT lists; wildcard `"*"`; list shorthand `[a,b]` ≡ in.

### Decisive source
```python
# Normalize $or/$not/$and → OR/NOT/AND and deduplicate.
# Memory._process_metadata_filters() renames OR→$or and NOT→$not,
# but effective_filters retains the original OR/NOT keys from
# deepcopy(input_filters).  Without dedup the same sub-conditions
# would be evaluated twice.
key_map = {"$or": "OR", "$not": "NOT", "$and": "AND"}
...
if ops & range_ops:            # gt/gte/lt/lte
    if non_range_ops:
        raise ValueError(...)  # never mix range+match in ONE condition — use AND
if self._is_datetime_range(range_kwargs):
    return FieldCondition(key=key, range=DatetimeRange(**range_kwargs))  # ISO strings → datetime range
```

**Flow:** normalize aliased `$`-keys with first-wins dedup → route AND/OR/NOT lists into Qdrant's must/should/must_not lanes recursively → leaf values: scalar→MatchValue, list→MatchAny, dict→op dispatch where ne/nin compile to MatchExcept and range ops to Range/DatetimeRange (all-ISO-string detection picks Datetime) → contains/icontains both become MatchText (tokenized full-text when an index exists, else exact substring) with an icontains case-sensitivity caveat logged. The memory layer pre-processes advanced filters only when `_has_advanced_operators` detects them.
**Invariant:** range and match operators can NEVER combine in one FieldCondition — the ValueError tells callers to split via AND; the `$or`/`OR` dual-key situation means backends MUST dedupe or every filtered query silently double-evaluates its OR clauses; wildcard "*" maps to match-all (skip), not an empty condition that would error.
**Probe:** `tests/vector_stores/test_qdrant.py::test_search_with_filters` (:224), `::test_create_filter_with_range_values` (:321), `::test_create_filter_multiple_filters` (:289).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mem0", query: "_create_filter _build_field_condition MatchExcept DatetimeRange or not dedup", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the operator-dispatch ladder including the mix-range-with-match refusal and $-key dedup; adapt per-backend condition constructors; omit MatchText nuances if your store has true substring ops.
