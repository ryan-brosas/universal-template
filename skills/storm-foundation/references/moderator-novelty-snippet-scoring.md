<!-- capsule-v2 -->
# Moderator novelty snippet scoring — which retrieved-but-unused facts should steer the conversation somewhere new?

**Source:** storm MIT `main@fb951af7`; Codebase Memory `storm`. **Question:** How do you pick, from everything ever retrieved, the snippets that are on-topic yet NOT already absorbed — to inject a fresh perspective instead of repeating the discussion?

## Claim-gated dissimilarity scoring over unused snippets
**Path/Symbol:** `knowledge_storm/collaborative_storm/modules/co_storm_agents.py:Moderator._get_conv_turn_unused_information` (:190-246) and `_get_sorted_unused_snippets` (:248-283).
**Signature:** `_get_conv_turn_unused_information(conv_turn: ConversationTurn, knowledge_base: KnowledgeBase) -> List[Information]`; `_get_sorted_unused_snippets(knowledge_base, conversation_history, last_n_conv_turn: int = 2)`.
**Data Shape:** Input: per-turn `raw_retrieved_info: List[Information]` (each with `snippets`, `meta`), KB cited registry `info_uuid_to_info_dict`, encoder embeddings. Output: descending-scored unused Information list.

### Decisive source
```python
cited_info_hash_set = set([hash(info) for info in cited_info])
unused_information = [info for info in raw_retrieved_single_snippet_info
                      if hash(info) not in cited_info_hash_set]
...
claim_similarity = np.where(claim_similarity >= 0.25, 1.0, 0.0)   # gate, not weight
query_sim_weight = 0.5; cited_snippets_sim_weight = 1 - query_sim_weight
combined_scores = ((1 - max_query_similarity) ** query_sim_weight) \
                * ((1 - cited_snippets_similarity) ** cited_snippets_sim_weight) \
                * claim_similarity
sorted_indices = np.argsort(combined_scores)[::-1]
```

**Flow:** (1) Explode every raw retrieved Information into per-snippet clones (`extract_storm_info_snippet`). (2) Drop any clone whose whole-Information hash is in the KB's cited set — hash equality IS identity here because Information's hash is md5 over (url, sorted snippets, meta). (3) Embed unused snippets plus the turn's claim, queries, and cited snippets. (4) Score = far-from-used-queries ^0.5 × far-from-already-cited ^0.5 × claim-gate(≥0.25 binarized). (5) Sort descending. Across turns, `_get_sorted_unused_snippets` walks back at most `last_n_conv_turn=2` turns STOPPING at a `"Questioning"` utterance_type, batch-encodes all strings once up front, then merges per-turn rankings round-robin via `zip_longest(..., fillvalue=None)` so each turn contributes alternately.
**Invariant:** (1) The claim gate is multiplicative BINARY filtering (score 0 kills the candidate), not a soft weight — snippets unrelated to what the speaker claimed can never win regardless of novelty. (2) Exclusion is by Information IDENTITY (content hash), not by URL or text prefix; two retrievals of the same content dedupe for free, while a same-URL different-snippet clone survives as genuinely new. (3) Empty unused set short-circuits BEFORE any embedding calls (:211-212). (4) The round-robin merge needs per-turn lists in comparable rank order and tolerates unequal lengths via fillvalue.
**Probe:** byte-pins executed this pass — :203 hash-set build, :206-210 identity filter comprehension, :236 `>= 0.25` gate, :238-244 exponent weights, :245 reversed argsort, :253 `last_n_conv_turn: int = 2`, :260 break-on-"Questioning". All line-exact against the checkout.
**Coverage caveat:** file checked `no_recorded_issue` @ gen 2026-08-25T20:09:07Z.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "storm", query: "Moderator _get_conv_turn_unused_information cosine_similarity claim query cited", limit: 10 });
```

## Verdict
Adopt the identity-hash exclusion + gated dissimilarity scoring for any "surface what the system has seen but not used" feature; adapt the 0.25 gate and 0.5/0.5 exponents as tuning knobs; omit nothing on the gate semantics — softening it back into a weight reintroduces off-topic "novel" noise, the exact failure the paper section targets.
