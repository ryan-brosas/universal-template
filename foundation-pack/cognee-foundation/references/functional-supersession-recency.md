<!-- capsule-v2 -->
# Functional-relationship supersession — recency wins, history is tagged not deleted

**Source:** cognee (Apache-2.0) `main@a8f9760b`; Codebase Memory `ext-cognee`. **Question:** For single-valued relationships ("ceo_of"), how do you resolve conflicting assertions over time while keeping full history queryable?

## resolve_temporal_contradictions
**Path/Symbol:** `cognee/tasks/graph/resolve_temporal_contradictions.py:resolve_temporal_contradictions` (:55-113); tagger `cognee/modules/graph/utils/temporal_conflict_resolver.py:tag_superseded_edges` (:39-100); spliced by `get_default_tasks` (cognify.py :421-428) only when `functional_relationships` given.
**Signature:** `async resolve_temporal_contradictions(data_points, functional_relationships=None, **kwargs) -> input unchanged`.
**Data Shape:** Tags written ONTO the superseded edge: `superseded`, `superseded_by`, `supersession_reason`. No-op unless functional set non-empty (cardinality cannot be inferred — LLM relationships carry none).

### Decisive source
```python
# Only facts one hop from touched entities; candidates must ALSO have their
# SUBJECT among touched ids so each subject is compared against its FULL history
# (subjects are fetch seeds ⇒ all their assertions are in the neighborhood):
candidate_edges = [e for e in edges if e[2] in functional and str(e[0]) in touched_node_ids]
superseded_edges = tag_superseded_edges(candidate_edges, functional)
# add_edges merges on (source, target, relationship_name) and REPLACES the property
# blob, so re-writing the tagged edges updates them in place. Nothing is deleted.
await graph_engine.add_edges(superseded_edges)
```

**Flow:** collect touched ids → 1-hop neighborhood → filter to declared-functional edges with touched subjects → tag older assertions with pointer to the surviving (most recent) one → re-add tagged edges as an in-place property update.
**Invariant:** (1) The subject-side filter is what makes cross-ingestion supersession work: a fact ingested today supersedes one from last month because both hang off the same deterministic `Entity:<name>` id. (2) Update-in-place relies on the graph engine's merge semantics for (source, target, relationship_name) — a store that appends duplicates instead would corrupt the invariant "one current + N tagged". (3) Advisory-pass discipline: errors are logged, never raised; the graph is already persisted.
**Probe:** `cognee/tests/unit/modules/graph/test_temporal_conflict_resolver.py::test_superseded_edges_keep_input_order`; `cognee/tests/unit/tasks/graph/test_resolve_temporal_contradictions.py::test_noop_without_functional_relationships`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-cognee", query: "resolve_temporal_contradictions functional_relationships tag_superseded_edges", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt declared-cardinality supersession with tag-don't-delete history; adapt tag names to your edge schema; omit entirely when all your relationships are many-valued (the default posture).
