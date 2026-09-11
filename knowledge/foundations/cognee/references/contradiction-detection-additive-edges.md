<!-- capsule-v2 -->
# Contradiction detection — additive-only conflict edges over the touched 1-hop region

**Source:** cognee (Apache-2.0) `main@a8f9760b`; Codebase Memory `ext-cognee`. **Question:** How do you surface contradicting facts in a growing graph without ever deleting or rewriting anything, and how is the LLM's answer anchored to real graph elements?

## detect_contradictions
**Path/Symbol:** `cognee/tasks/graph/detect_contradictions.py:detect_contradictions` (:146-243), `_build_candidate_facts` (:77-123), `_contradiction_endpoints` (:126-142); spliced by `get_default_tasks` (cognify.py :407-415) AFTER add_data_points when `contradiction_detection` on.
**Signature:** `async detect_contradictions(data_points, **kwargs) -> List[DataPoint]` (returns input UNCHANGED).
**Data Shape:** Facts rendered `[F#] {source} {rel with _ → space} {target}`; contradiction edge tuple `(source_id, target_id, "contradicts", {first_fact, second_fact, reason, confidence, ...})`.

### Decisive source
```python
STRUCTURAL_RELATIONSHIPS = frozenset({"contains","is_part_of","made_from","exists_in","contradicts"})
# candidates: ≥1 touched endpoint + BOTH endpoints named (drops structural nodes)
# hard cap: cognify_config.contradiction_max_facts, logged when hit
...
endpoints = _contradiction_endpoints(first_edge, second_edge)
def _contradiction_endpoints(first_edge, second_edge):
    if first_source != second_source: return first_source, second_source  # differing subjects
    if first_target != second_target: return first_target, second_target  # same subject ⇒ objects differ
    return None                                                            # same pair: nothing to link
if contradiction.confidence < cognify_config.contradiction_confidence_threshold: continue
if first_edge is None or second_edge is None: continue   # model cited an id we never gave it
```

**Flow:** collect touched entity ids from chunk `contains` (TextSummary wraps via made_from) → `get_neighborhood(touched, depth=1)` — new AND pre-existing facts comparable because Entity ids are deterministic (`Entity:<name>`) → render/filter/cap facts → single structured LLM call (`ContradictionList`) → threshold + id-validation + endpoint selection → batch `add_edges(contradiction_edges)`.
**Invariant:** (1) NON-DESTRUCTIVE: only adds edges; runs LAST so both facts are persisted before comparison; whole task swallows its own errors ("auxiliary and must never break ingestion"). (2) Every LLM output field must be validated against locally-rendered state (ids we issued, our fact text, confidence threshold) before touching the graph. (3) Endpoint rule prefers subject-disagreement links, falls back to object links, refuses self-links.
**Probe:** `cognee/tests/unit/tasks/graph/test_detect_contradictions.py::test_build_candidate_facts_filters_to_touched_named_edges`, `::test_build_candidate_facts_respects_limit`; wiring `cognee/tests/unit/modules/cognify/test_contradiction_detection_wiring.py::test_flag_on_appends_detection_after_storage`.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "ext-cognee", query: "_build_candidate_facts _contradiction_endpoints contradicts STRUCTURAL_RELATIONSHIPS", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt touched-region scoping + rendered-fact anchoring + additive conflict edges; adapt structural-relationship vocabulary and thresholds; omit if your pipeline has no LLM gate available.
