<!-- capsule-v2 -->
# Payload-graph percolation heuristics — when is an extra payload-filtered HNSW graph worth building?

**Source:** Qdrant Apache-2.0 `master@74f3e85b`; Codebase Memory `qdrant`. **Question:** When building per-field (payload-block) HNSW subgraphs for filtered search, which blocks deserve a graph and which are skipped?

## Percolation-gated additional links
**Path/Symbol:** `lib/segment/src/index/hnsw_index/hnsw/build.rs`: `HNSWIndex::build` additional-links section (:364-540), `condition_points` (:602-626), block heuristics (:439-498).
**Signature:** `for_each_payload_block(&field, full_scan_threshold, &mut process_block)` with `process_block(PayloadBlockCondition) -> OperationResult<()>`.
**Data Shape:** input: indexed fields with `payload_schema.enable_hnsw()`, payload blocks carrying a `condition` + estimated `cardinality`; state: measured `average_links_per_0_level`, sampled main-graph connectivity.

### Decisive source
```rust
// According to percolation theory, random graph becomes disconnected
// if 1/K points are left, where K is average number of links per point
// ... we choose sampling point at 2/K, which expects graph to still be
// mostly connected, but still have some measurable disconnected components.
let percolation = 1. - 2. / (average_links_per_0_level_int as f32);
let required_connectivity = /* max of 3 samples of subgraph_connectivity at `percolation` */;

const PERCOLATION_MULTIPLIER: usize = 4;
let max_block_size = if config.m > 0 {
    total_vector_count / average_links_per_0_level_int * PERCOLATION_MULTIPLIER
} else { usize::MAX };
// ...
if payload_block.cardinality > max_block_size { return Ok(()); }        // too big: plain HNSW suffices
if points_to_index.len() <= full_scan_threshold / DELETED_POINTS_FACTOR { return Ok(()); } // too small/deleted
if !is_tenant && index_pos > 0 && let Some(required_connectivity) = required_connectivity {
    let graph_connectivity = graph_layers_builder.subgraph_connectivity(rng, &points_to_index, percolation);
    if graph_connectivity >= required_connectivity { return Ok(()); }   // already connected via main graph
}
```

**Flow:** measure true mean degree of level-0 (`get_average_connectivity_on_level`) → derive percolation sampling point 2/K → sample main-graph connectivity 3× and keep the max as the requirement → iterate each indexed field's payload blocks → skip oversized (> count/K×4), mostly-deleted (< full_scan_threshold/4 live points; `DELETED_POINTS_FACTOR=4` tolerates up to 75% deleted), or already-connected blocks → otherwise build a single-level `GraphLayersBuilder::new_with_params(..., num_entries=1, ..., mergeable=false)` filtered graph restricted to the block's points via a `BuildConditionChecker` over a shared visited list, then `merge_from_other`.
**Invariant:** (1) tenant fields (`is_tenant`) ALWAYS get their graph — low-cardinality filters dominate real queries there; (2) connectivity skip applies only from the second field on (`index_pos > 0`) and only when the main graph has m>0; (3) deleted-point tolerance is 75%, not 100% — beyond that the block graph would be built on noise; (4) cardinality estimation + point iteration must exclude vector-deleted points (`condition_points` filters against `deleted_vector_bitslice()`).

**Probe:** `grep -c "PERCOLATION_MULTIPLIER\|DELETED_POINTS_FACTOR" lib/segment/src/index/hnsw_index/hnsw/build.rs` → prints `4`. Direct test: `lib/segment/tests/integration/payload_index_test.rs::test_cardinality_estimation` (:823) pins the cardinality estimates feeding these gates.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "qdrant", query: "subgraph_connectivity for_each_payload_block PayloadBlockCondition merge_from_other", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three gate order (size → liveness → connectivity) and the 2/K sampling-point rationale. Adapt K measurement and block iteration to host payload-index structures. Omit GPU-accelerated block builds. Coverage caveat: no unit test pins the multipliers themselves; they are load-bearing constants documented only here and in-source.
