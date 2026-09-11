<!-- capsule-v2 -->
# Feedback & importance weights — stored on DataPoints, consumed at ranking time

**Source:** cognee (Apache-2.0) `main@a8f9760b`; Codebase Memory `ext-cognee`. **Question:** How do user feedback signals flow from storage into retrieval ranking without coupling the ingestion pipeline to the feedback subsystem?

## feedback_weight / importance_weight plumbing
**Path/Symbol:** `cognee/infrastructure/engine/models/DataPoint.py` (fields `feedback_weight: float = 0.5`, `importance_weight: float | None = 0.5`, :60-67); projection `brute_force_triplet_search.py:get_memory_fragment` (:70-74 — feedback_weight projected ONLY when influence > 0); scoring `CogneeGraph._effective_distance` (:429-451); apply pipeline `cognee/tasks/memify/apply_feedback_weights.py` (:1-245); chunk default `DocumentChunk.importance_weight: Optional[float] = 0.5`.
**Signature:** blend `(1-infl)*d + infl*(1-w)` in normalized [0,1] distance space; `personal_factor(w, influence, distance_space=...)` for per-node prefers.
**Data Shape:** Weight 0.5 = neutral everywhere; missing/non-numeric ⇒ 0.5 fallback at score time.

### Decisive source
```python
# Projection-side gate — the property isn't even fetched when the feature is off:
if feedback_influence > 0.0:
    if "feedback_weight" not in node_properties_to_project:
        node_properties_to_project.append("feedback_weight")
    if "feedback_weight" not in edge_properties_to_project:
        edge_properties_to_project.append("feedback_weight")
```

**Flow:** memify `apply_feedback_weights_pipeline` persists feedback onto DataPoint weights → triplet path projects weights only under a positive influence → scorer blends into effective distance with eligibility guard (real cosine distances only) → hybrid path multiplies importance into RRF scores (`0.75 + 0.5*importance`) and keeps personal weights in their own attribute (`personal_weight`, deliberately NOT `feedback_weight`, so signals stay separable when debugging).
**Invariant:** (1) Default-off means byte-identical rankings: flag off ⇒ weight never projected ⇒ scorer sees no attribute ⇒ unchanged ordering. (2) Neutral value 0.5 must be an exact no-op in every consumer (tested). (3) Importance and personal/feedback are DISTINCT channels; merging their attributes makes ranking regressions undebuggable.
**Probe:** `cognee/tests/unit/memify_pipelines/test_apply_feedback_weights_pipeline.py`; `cognee/tests/unit/modules/retrieval/hybrid/test_personal_weight_ranking.py::test_neutral_weight_is_an_exact_no_op`.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "ext-cognee", query: "feedback_weight importance_weight apply_feedback_weights personal_factor", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt DataPoint-carried weights + projection-gated consumption + neutral-value no-op guarantees; adapt factor formulas to your ranker; omit the memify write path if you set weights manually.
