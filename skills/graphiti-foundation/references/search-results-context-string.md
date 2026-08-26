<!-- capsule-v2 -->
# SearchResults context projection — how do you serialize typed hybrid results into ONE LLM context string without leaking unprojected fields?

**Source:** graphiti Apache-2.0 `main@993e081a`; Codebase Memory `graphiti`. **Question:** which fields of nodes/edges/episodes/communities reach the prompt, and how is the boundary kept closed?

## XML-tagged context builder over the to_prompt_json choke point
**Path/Symbol:** `graphiti_core/search/search_helpers.py:search_results_to_context_string` (:27-72) + `format_edge_date_range` (:22-24); serializer `prompts/prompt_helpers.py:to_prompt_json`.
**Signature:** `def search_results_to_context_string(search_results: SearchResults) -> str`.
**Data Shape:** closed per-section projections — facts carry {fact, valid_at str, invalid_at str-or-Present-sentinel}; entities {entity_name, summary}; episodes {source_description, content}; communities {community_name, summary}.

### Decisive source
```python
# search_helpers.py :29-36 + :52-70 (trimmed) — closed projections + tagged wrapper:
fact_json = [
    {
        'fact': edge.fact,
        'valid_at': str(edge.valid_at),
        'invalid_at': str(edge.invalid_at or 'Present'),
    }
    for edge in search_results.edges
]
# ... entity_json / episode_json / community_json same pattern ...
context_string = f"""
    FACTS and ENTITIES represent relevant context to the current conversation.
    ... Facts with an invalid_at date of "Present" are considered valid.
    <FACTS>
            {to_prompt_json(fact_json)}
    </FACTS>
    <ENTITIES>
            {to_prompt_json(entity_json)}
    </EPISODES> ... </EPISODES>
    <COMMUNITIES> ... </COMMUNITIES>
"""

# :22-24 display-side rendering uses DIFFERENT sentinels:
# returns f'{edge.valid_at if edge.valid_at else "date unknown"} - '
#      f'{(edge.invalid_at if edge.invalid_at else "present")}'   # lowercase
```

**Flow:** project each `SearchResults` list through explicit dict literals (uuids, embeddings, attributes, group_ids never included) → serialize each section through `to_prompt_json` (the single ensure_ascii=False choke point) → wrap sections in FACTS/ENTITIES/EPISODES/COMMUNITIES tags preceded by a natural-language legend explaining fact validity windows and the Present sentinel → return one string ready to concatenate into any prompt.
**Invariant:** the projection lists are CLOSED — adding a field to EntityEdge/EntityNode does not leak into prompts until someone extends the literal here; that friction is the feature. Two sentinel conventions coexist DELIBERATELY: machine-parsed context capitalizes 'Present' while the human-display helper renders 'date unknown'/'present' lowercase — porters must not unify them without checking downstream parsers.
**Probe:** offline venv probe RE-EXECUTED pass 11 (verification pass): build SearchResults with one EntityEdge (invalid_at=None), one node, one episode, one community, render via `search_results_to_context_string` → all four section tags present, capitalized "Present" sentinel emitted for the None invalid_at, fact/community text present, and unprojected keys (uuid) ABSENT from the 782-char output — PASS. In-repo callers are test-only (`tests/test_graphiti_int.py:77`) — host-facing helper, caveat recorded.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "graphiti", query: "search_results_to_context_string format_edge_date_range to_prompt_json", limit: 10 });
```

## Verdict
Adopt closed-projection dict literals plus tag-with-legend wrapping for any typed-results-to-prompt surface. Adapt section set and sentinels to your domain vocabulary. Omit the COMMUNITIES section when clustering is disabled rather than emitting empty tags.
