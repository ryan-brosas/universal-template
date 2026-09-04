<!-- capsule-v2 -->
# NL vector prioritization — how are LLM-conflict candidates ordered before resolution?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** When several natural-language-trigger policies could match, what order do candidates enter LLM conflict resolution in — and what happens when the embedding service is down?

## Sort key: vector-search hit beats priority, inside `_evaluate_natural_language_policies`
**Path/Symbol:** `src/cuga/backend/cuga_graph/policy/agent.py:_evaluate_natural_language_policies` (sort at :856-858; candidate collection :820-834; non-critical failure :868-869).
**Signature:** `policies_with_nl_triggers.sort(key=lambda x: (x[0].id in vector_policy_ids, x[0].priority), reverse=True)`.
**Data Shape:** `vector_policy_ids: Set[str]` from a type-filtered top-20 `storage.search_policies(query_embedding, limit=20, enabled_only=True)`; `policies_with_nl_triggers: List[(Policy, List[NaturalLanguageTrigger])]` filtered by trigger target (`intent` target accepts both `intent` and `user_input`).

### Decisive source
```python
# agent.py:856-858
policies_with_nl_triggers.sort(
    key=lambda x: (x[0].id in vector_policy_ids, x[0].priority), reverse=True
)

# agent.py:868-869 — vector search is an optimization, never a gatekeeper
except Exception as e:
    logger.debug(f"Vector search failed (non-critical): {e}")
```

**Flow:** collect policies with NL triggers for this target → embed query text → vector search top-20 across ALL types → filter to requested policy types → build id set → sort: boolean membership in the vector set FIRST (True > False), priority SECOND → hand the ordered list to `_resolve_nl_trigger_conflicts` for the LLM decision.
**Invariant:** Vector retrieval only REORDERS candidates; it can never create or remove them. If embeddings fail, resolution proceeds on priority order alone — degradation of ranking, not of function. This complements the matcher's IntentGuard precedence (see `matcher` capsule): keyword guards bypass this path entirely.
**Probe:** No dedicated probe test exists for this exact sort (pass-1 flagged it as "deserves a probe test if absent" — still absent upstream). Adjacent coverage: `test_similarity_integration.py` pins that storage ranking reflects similarity; `test_nl_trigger_conflict_fallback.py` pins the downstream fallback ladder. Coverage caveat recorded.
**Why it matters to a porter:** without the boolean-first tuple, high-priority but semantically irrelevant policies would reach the LLM first and win conflicts they should lose; without the try/except, an embedding outage would silently disable every NL policy.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "_evaluate_natural_language_policies", limit: 3 });
```

## Verdict
Adopt the (vector-hit, then priority) descending sort as the candidate-ordering contract for semantic-policy matching, and the fail-open debug-log posture around embedding calls. Adapt limits (20) and type filtering to your scale. Omit nothing — the seam is two lines plus its exception path.
