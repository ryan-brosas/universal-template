<!-- capsule-v2 -->
# Merge-during-retrieval — conversational reserve in ranked result fusion

**Source:** cognee (Apache-2.0) `main@a8f9760b`; Codebase Memory `ext-cognee`. **Question:** When a follow-up turn retrieves fresh results but the user is mid-conversation, how do you fuse new and prior context without the conversation crowding out new evidence?

## merge_ranked / edge_identity / conversational_reserve
**Path/Symbol:** `cognee/modules/retrieval/utils/merge_results.py:merge_ranked`, `edge_identity`, `conversational_reserve`; consumer `graph_completion_retriever.py:merge_retrieved_objects` (:294-301).
**Signature:** `merge_ranked(primary, secondary, identity=edge_identity, limit=top_k, secondary_reserve=conversational_reserve(top_k)) -> list`.
**Data Shape:** Elements deduped by identity key (for edges: `(node1.id, node2.id, relationship)` — direction-sensitive for directed edges); hybrid variant merges per-lane with its own limits (`merge_hybrid_results(chunks_limit, entities_limit, facts_limit)`).

### Decisive source
```python
# consumer wiring:
def merge_retrieved_objects(self, primary, secondary):
    return merge_ranked(primary, secondary,
                        identity=edge_identity,
                        limit=self.top_k,
                        secondary_reserve=conversational_reserve(self.top_k))
```

**Flow:** rank-ordered lists merge by first-seen identity (primary wins ties) → the merged output is capped at top_k → within that cap a RESERVED SLICE goes to conversational (secondary) elements so history keeps a guaranteed minority share while fresh retrieval dominates.
**Invariant:** (1) Reserve must be a fraction of limit, never equal — 100% reserve erases new evidence; 0% lets chatty sessions freeze context on stale triplets. (2) Identity-based dedup runs BEFORE capping or duplicates silently eat slots. (3) Each retriever supplies its own identity function; reusing an edge identity on chunk lists would collapse distinct chunks.
**Probe:** `cognee/tests/unit/modules/retrieval/test_merge_results.py` (whole file).

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "ext-cognee", query: "merge_ranked edge_identity conversational_reserve merge_results", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt identity-deduped capped fusion with an explicit secondary reserve; adapt reserve ratio to your UX; omit if you don't carry retrieved context across turns.
