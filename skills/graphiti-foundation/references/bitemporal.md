<!-- capsule-v2 -->
# Bi-temporal edge resolution — contradiction handling

**Source:** graphiti MIT `<branch>@<commit>`; Codebase Memory `graphiti`. **Question:** how does a memory graph resolve contradictory facts (Alice is CEO, later ex-CEO) using bi-temporal edges?

## Connected graph-selected seam
**Path/Symbol:** `graphiti_core/utils/maintenance/edge_operations.py`: `resolve_extracted_edges` (:325-444), `resolve_edge_contradictions` (:538-577), `_extract_edge_timestamps` (:579-620); `graphiti_core/edges.py`: `EntityEdge` (:263-303).
**Signature:** `resolve_edge_contradictions(...)` — detects and resolves fact-edges that contradict (same subject/predicate, different object) using their bi-temporal timestamps.
**Data Shape:** each fact-edge carries FOUR timestamps — `valid_at` (when the fact became true IN THE WORLD, event time) plus the bi-temporal pair; contradictions detected across edges sharing subject+predicate.

### Decisive source
```ts
# For memory systems whose facts CHANGE (Alice is CEO, later ex-CEO),
# every fact-edge carries four timestamps (edges.py:271-282):
#   valid_at — when the fact became true IN THE WORLD (event time)
# resolve_edge_contradictions detects same subject+predicate edges with different
#   objects and resolves them by their valid_at ordering
```

**Flow:** after extraction, `resolve_extracted_edges` dedups; `resolve_edge_contradictions` finds fact-edges that contradict (same subject/predicate, different object) and resolves them by `valid_at` ordering — the newer fact supersedes the older. `_extract_edge_timestamps` reads the timestamps to drive the decision.
**Invariant:** contradictory facts are resolved by event time (`valid_at`), never dropped silently; the newer fact wins while the older remains as history.
**Probe:** `tests/` graphiti tests (contradictory edges resolved by valid_at; older fact retained as history).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "graphiti", query: "resolve_edge_contradictions valid_at bi-temporal edges resolve", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the bi-temporal contradiction resolution (detect same-subject/predicate edges, resolve by valid_at); adapt the timestamp semantics and resolution policy to host.
