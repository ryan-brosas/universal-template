<!-- capsule-v2 -->
# DataFrame modularity with NX-parity semantics — how do you compute modularity on an edge-list DataFrame so results match NetworkX to 1e-10?

**Source:** graphrag MIT `main@6dad6d2b059589624035714d8dcfde94ecc0a5fb`; Codebase Memory `graphrag`. **Question:** what normalization makes a pandas-only modularity implementation bit-comparable with networkx, and which duplicate/direction rules carry that guarantee?

## _modularity_components + metric dispatch
**Path/Symbol:** `packages/graphrag/graphrag/graphs/modularity.py` (`_df_to_edge_list` :26-45, `modularity` :48-81, `_modularity_component` :84-96, `_modularity_components` :99-154, `calculate_{root,leaf,graph,lcc,weighted}_modularity` :157-260, `calculate_modularity` :263-295).
**Signature:** `modularity(edges: pd.DataFrame, partitions: dict[str, int], resolution: float = 1.0) -> float`; weighted-components default metric = `sum(component_mod * component_size) / total_nodes`.
**Data Shape:** edges need source/target/weight columns; partitions map node title → community id; returns per-community components dict or summed float.

### Decisive source
```python
# modularity.py:112-117 — undirected normalization FIRST: min/max per row
# canonicalizes direction, then keep="last" dedups REVERSED duplicates too
lo = df[[source_column, target_column]].min(axis=1)
hi = df[[source_column, target_column]].max(axis=1)
df = df.assign(**{source_column: lo, target_column: hi})
df = df.drop_duplicates(subset=[source_column, target_column], keep="last")
```
```python
# :133-137 — self-loops count weight ONCE into intra-degree, real edges
# TWICE (each endpoint's degree view); getting this 1x/2x backwards breaks
# NX parity silently for any graph with loops
if src_comm == tgt_comm:
    if src == tgt:
        degree_sums_within[src_comm] += weight
    else:
        degree_sums_within[src_comm] += weight * 2.0
```

**Flow:** raw relationships → direction-canonicalize + last-wins dedup (matches nx.Graph edge overwrite) → single pass accumulating within/for-community degree sums + total weight → zero/negative total weight short-circuits to ALL-ZERO per-community dict (`dict.fromkeys(communities, 0.0)` :143-144), not an error → per-community `(intra - γ·k²/2m)/2m` formula summed.
**Invariant:** the whole-graph metrics re-run hierarchical_leiden with the SAME pinned seed (default `0xDEADBEEF`) as clustering — modularity is only meaningful against the partitions Leiden actually produced; `calculate_weighted_modularity` filters components ≤ `min_connected_component_size` and falls back to WHOLE-GRAPH when nothing qualifies (:236-238), so tiny disconnected graphs still return a score.
**Probe:** `tests/unit/graphs/test_modularity.py` — side-by-side NX reference asserts `< 1e-10` parity incl. reversed edges (:164), custom resolutions (:201), duplicates keeping-last (:219), reversed duplicates (:234), golden fixture (:249). Executed @pin: `/home/utopia/.venvs/grag-lane-venv/bin/python -m pytest tests/unit/graphs/ -q` → 37 passed.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "graphrag", query: "modularity components intra community degree resolution", limit: 10, fields: ["signature", "name", "file"] });
```
Live-resolved rank#2 `_modularity_components` :99-154 behind its own test.

## Verdict
Adopt the normalize→dedup-last→degree-ladder pipeline and the 1x-loop/2x-edge rule verbatim — they ARE the parity contract; adapt column names/metric dispatch to host; omit root-vs-leaf hierarchy plumbing unless you also port pinned-seed Leiden. No coverage caveat.
