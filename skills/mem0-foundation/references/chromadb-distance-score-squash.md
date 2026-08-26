<!-- capsule-v2 -->
# Chroma distance→score squashing — why is score 1/(1+d) and what does the nested-list parser tolerate?

**Source:** mem0 MIT `main@8d5b7865`; Codebase Memory `mnt-hdd-utopia-inspo-memory-mem0`. **Question:** how are Chroma's raw distances and shape-varying query results normalized into the OutputData(score∈[0,1]) contract?

## Connected graph-selected seam
**Path/Symbol:** `mem0/vector_stores/chroma.py`: `ChromaDB._parse_output` (:76-109); consumer `search` (:145-163).
**Signature:** `_parse_output(data: Dict) -> List[OutputData]` where data = Chroma query dict `{ids, distances, metadatas}`.
**Data Shape:** Chroma returns each key as EITHER a flat list (single query embedding) OR a list-of-lists (batched); entries may be missing/shorter than others; get() results carry no distances at all.

### Decisive source
```python
for key in keys:                      # ["ids", "distances", "metadatas"]
    value = data.get(key, [])
    if isinstance(value, list) and value and isinstance(value[0], list):
        value = value[0]              # unwrap ONE nesting level
    values.append(value)
ids, distances, metadatas = values
max_length = max(len(v) for v in values if isinstance(v, list) and v is not None)
...
raw_distance = distances[i] if ... i < len(distances) else None
score = 1.0 / (1.0 + raw_distance) if raw_distance is not None else None
```

**Flow:** per-key unwrap of one nesting level → length = max over present lists → index-wise zip with per-field bounds guards producing None for absent slots → distance→similarity squash → list[OutputData].
**Invariant:** score is a MONOTONE-DECREASING similarity in [0,1] via logistic squash 1/(1+d), NOT a linear 1−d — cross-backend ranking comparability (the whole point of mem0's fusion) depends on every backend mapping its native metric into "higher = more similar" with this documented formula; the fleet-wide regression suite pins it (`tests/vector_stores/test_score_normalization.py::TestChromaDB::test_score_formula` :103 asserts the exact 1/(1+d) arithmetic). The parser must never IndexError on ragged/missing fields — absence degrades to None per-field.
**Probe:** `grep -n "1.0 / (1.0 + raw_distance)" mem0/vector_stores/chroma.py` (exactly :101).
**Direct test:** `tests/vector_stores/test_chroma.py::test_search_vectors` (:33, score == approx(1.0/1.1) for distance 0.1) and the TestChromaDB block of test_score_normalization.py (:82-109).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-memory-mem0", query: "_parse_output ChromaDB distances metadatas", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the squash formula and ragged-tolerant parse verbatim — both are pinned by name upstream; adapt only the key names to your backend's response envelope; omitting the squash (or substituting 1−d) breaks cross-backend score comparability silently. Fully direct-tested (no caveat).
