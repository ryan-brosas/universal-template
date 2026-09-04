<!-- capsule-v2 -->
# Stable LCC + union-find components — how do you make "the largest connected component" reproducible regardless of input row order?

**Source:** graphrag MIT `main@6dad6d2b059589624035714d8dcfde94ecc0a5fb`; Codebase Memory `graphrag`. **Question:** what does the stability ladder look like (union-find → LCC filter → name normalize → direction canonicalize → dedup → sort) and which step would a porter drop?

## connected_components + stable_lcc
**Path/Symbol:** `packages/graphrag/graphrag/graphs/connected_components.py` (`connected_components` :9-63 with path-compressed find :41-45, `largest_connected_component` :65-93) + `graphs/stable_lcc.py` (`stable_lcc` :22-70, `_normalize_name` :73-75).
**Signature:** `connected_components(relationships: pd.DataFrame, source_column="source", target_column="target") -> list[set[str]]` sorted by DESCENDING size; `stable_lcc(...) -> pd.DataFrame`.
**Data Shape:** in/out both edge DataFrames; components as node-title sets; ties in size resolve by sort order of the grouping (deterministic given deterministic input).

### Decisive source
```python
# connected_components.py:41-45 — iterative find with GRANDPARENT
# compression (parent[x] = parent[parent[x]]); no recursion, no rank —
# fine for knowledge-graph scale, wrong to port into adversarial unions
def find(x: str) -> str:
    while parent[x] != x:
        parent[x] = parent[parent[x]]
        x = parent[x]
    return x
```
```python
# stable_lcc.py:60-67 — swap via boolean mask THEN dedup the reversed
# pairs the swap just merged; dropping either step leaves (A,B),(B,A)
# double rows that break downstream degree counts
swapped = edges[source_column] > edges[target_column]
edges.loc[swapped, [source_column, target_column]] = edges.loc[
    swapped, [target_column, source_column]].to_numpy()
edges = edges.drop_duplicates(subset=[source_column, target_column])
return edges.sort_values([source_column, target_column]).reset_index(drop=True)
```

**Flow:** normalize names FIRST (`html.unescape().upper().strip()` — so `&amp;Co` and `&CO;` variants collapse BEFORE component computation, stable_lcc :47-58) → union-find over deduped edges → keep only edges whose BOTH endpoints are in component[0] → canonicalize direction → dedup → alphabetical two-column sort → reset_index. Empty input short-circuits to a COPY (:44-45), never None.
**Invariant:** normalization happens BEFORE the LCC filter — reversing the order computes components on unnormalized names and can pick a DIFFERENT largest component; `zip(..., strict=True)` on the union loop makes column-length mismatch an error not silent truncation.
**Probe:** `tests/unit/graphs/test_stable_lcc.py` — flipped-rows and shuffled-rows produce identical output (:60/:79), node-name normalization asserted (:101), NX side-by-side set equality (:144-182); `tests/unit/graphs/test_connected_components.py` 9 tests incl. two-component splits. Executed @pin: `$VENV_ROOT/grag-lane-venv/bin/python -m pytest tests/unit/graphs/ -q` → 37 passed.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "graphrag", query: "stable largest connected component normalize deterministic", limit: 10, fields: ["signature", "name", "file"] });
```
Live-resolved rank hits on `largest_connected_component` :65-93 + `stable_lcc._normalize_name` :73-75.

## Verdict
Adopt the full ladder INCLUDING normalize-before-filter ordering and mask-swap+dedup pairing; adapt the normalizer (HTML unescape may be domain-specific) but keep it inside the pipeline before any topology decision; omit rank-balanced union-find unless graphs exceed ~1M nodes. No coverage caveat.
