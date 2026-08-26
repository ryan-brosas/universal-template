<!-- capsule-v2 -->
# Multi-episode edge extraction — attribution indices, clamping, reference-time selection

**Source:** graphiti MIT `main@993e081a`; Codebase Memory `mnt-hdd-utopia-inspo-memory-graphiti`. **Question:** when several episodes are extracted in ONE LLM call, how are facts attributed back to their source episodes without losing or misdating them?

## Multi-episode edge extraction
**Path/Symbol:** `graphiti_core/utils/maintenance/edge_operations.py`: `extract_edges` (:117-322); episode-attribution instruction injection (:170-181); name validation + self-edge drop (:211-242); index→uuid mapping with clamp+fallback (:290-297); `reference_time` from first claimed index (:309-313).
**Signature:** `async extract_edges(clients, episode: EpisodicNode | list[EpisodicNode], nodes, previous_episodes, edge_type_map, group_id='', edge_types=None, custom_extraction_instructions=None) -> list[EntityEdge]`.
**Data Shape:** LLM returns `ExtractedEdges` whose edges carry `episode_indices: list[int]` (0-based into the concatenated episode list); `build_episodic_edges` mirrors this with `node_episode_index_map: dict[node_uuid, list[int]]` (:52-96) so MENTIONS edges also attach per-node to only the attributed episodes.

### Decisive source
```python
# Prompt contract injected ONLY for multi-episode calls (appended to custom instructions):
episode_attribution = (
    '\n8. **Episode Attribution**: ... set `episode_indices` '
    'to the 0-based list of episode numbers that the fact was derived from. '
    'A fact sourced from Episodes 0 and 1 should have `episode_indices: [0, 1]`.'
)

# Clamp out-of-range indices; empty/invalid result falls back to ALL episodes
# (attribution degrades to broadcast rather than dropping the fact):
edge_episode_uuids = []
for idx in edge_data.episode_indices:
    if 0 <= idx < len(episodes):
        edge_episode_uuids.append(episodes[idx].uuid)
if not edge_episode_uuids:
    edge_episode_uuids = [ep.uuid for ep in episodes]

# Reference time comes from the FIRST claimed episode, not the batch max:
reference_time=(
    episodes[edge_data.episode_indices[0]].valid_at
    if edge_data.episode_indices and 0 <= edge_data.episode_indices[0] < len(episodes)
    else primary_episode.valid_at
),
```

**Flow:** normalize single-or-list → build reversed signature map (`edge_type_map {(src,tgt): [type_names]}` → `{type_name: [(src,tgt),...]}`, unknown types default `[('Entity','Entity')]`) → context uses `max(episodes, key=valid_at)` as primary reference time and per-episode headers with timestamps via `concatenate_episodes` → ONE call at `extract_edges_max_tokens = 16384` → validate every returned endpoint name against `name_to_node` (drop with warning) and drop self-edges where endpoints resolve to the same uuid → skip facts that `.strip()` to empty → parse `valid_at`/`invalid_at` ISO strings with `replace('Z','+00:00')` + `ensure_utc`, ValueError ⇒ warn-and-skip that timestamp (not the edge) → map indices to uuids (clamp+broadcast fallback) and construct `EntityEdge(created_at=utc_now())`.
**Invariant:** (1) an edge is NEVER dropped because its attribution indices are bad — worst case it links to all episodes in the batch; (2) `valid_at` parse failure drops the TIMESTAMP but keeps the edge (logged); (3) self-edges are dropped by resolved UUID equality even when names differ; (4) group_id precedence: explicit arg beats `primary_episode.group_id`; (5) `build_episodic_edges` bounds-checks each index against `len(episode_uuids)` — same defensive posture on the MENTIONS side.
**Probe:** `.venv/bin/python -m pytest tests/utils/maintenance/test_edge_operations.py::test_extract_edges_drops_self_edges tests/utils/maintenance/test_edge_operations.py::test_extract_edges_keeps_valid_edges_with_same_name_different_nodes tests/utils/maintenance/test_edge_operations.py::test_edge_type_signatures_map_preserves_multiple_signatures -q`. Anchored at repo root. Battery: `grep -c "routing_='r'," graphiti_core/utils/maintenance/edge_operations.py` → 2 (Neptune/Kuzu read paths of filter_existing_duplicate_of_edges); `grep -n 'extract_edges_max_tokens = 16384' graphiti_core/utils/maintenance/edge_operations.py` → line 141.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-memory-graphiti", query: "extract_edges episode_indices concatenate_episodes edge_type_map", limit: 8, fields: ["signature", "name", "file"] });
// rank family: edge_operations.extract_edges :117-322
```

## Verdict
Adopt the indices-in/clamp-or-broadcast-out attribution contract and first-claimed-episode reference time; adapt prompt numbering and header format to your extraction prompt; omit multi-episode batching entirely if you ingest one small episode at a time (then `episode_indices` degenerates to [0]). Direct tests run in default CI.
