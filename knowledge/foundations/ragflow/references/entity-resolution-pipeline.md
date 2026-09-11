<!-- capsule-v2 -->
# Entity resolution pipeline — how do you merge duplicate graph entities with cheap string gates before spending LLM calls, and checkpoint each batch?

**Source:** ragflow Apache-2.0 `main@9ea83b7a9d003d948fe4c99c6f35de02115a96e8`; Codebase Memory `ragflow`. **Question:** What is the candidate-generation filter, batching/concurrency shape, and per-batch checkpoint contract for LLM-based entity resolution?

## Cheap gates → batched LLM verdicts → component merge
**Path/Symbol:** `rag/graphrag/entity_resolution.py:EntityResolution.__call__` (:73-197), `is_similarity` (:275-289), `_resolve_candidate` (:199-243), `_process_results` (:245-263).
**Signature:** `async def __call__(self, graph: nx.Graph, subgraph_nodes: set[str], prompt_variables=None, callback=None, task_id="", checkpoints=None, save_checkpoint=None) -> EntityResolutionResult`.
**Data Shape:** Batches of 100 candidate pairs per entity type; ≤5 concurrent batches (`asyncio.Semaphore(5)`); checkpoints map content-addressed key → list of merged pairs; verdict text uses `<|N|>` index + `&&yes&&` delimiters.

### Decisive source
```python
# gate 1 — only pairs touching NEW nodes are candidates:
candidate_resolution[k] = [(a, b) for a, b in itertools.combinations(v, 2)
                           if (a in subgraph_nodes or b in subgraph_nodes)
                           and self.is_similarity(a, b)]

# gate 2 — the similarity ladder:
def is_similarity(self, a, b):
    if self._has_digit_in_2gram_diff(a, b):     # digit-bearing bigram mismatch ⇒ veto
        return False
    if is_english(a) and is_english(b):
        return Levenshtein.distance(a, b) <= min(len(a), len(b)) // 2
    a, b = set(a), set(b)                       # CJK char-set overlap
    max_l = max(len(a), len(b))
    if max_l < 4:
        return len(a & b) > 1
    return len(a & b) * 1.0 / max_l >= 0.8

# per-batch replay + fail-forward timeout:
checkpoint_key = resolution_checkpoint_key(candidate_batch[0], candidate_batch[1])
checkpoint = checkpoints.get(checkpoint_key)
if isinstance(checkpoint, list):
    ...replay into result_set; return            # no LLM call
selected_pairs = await asyncio.wait_for(self._resolve_candidate(...), timeout=timeout_sec)
if selected_pairs is not None and save_checkpoint:
    await save_checkpoint(checkpoint_key, [list(p) for p in selected_pairs])
```

**Flow:** cluster nodes by `entity_type` → pairwise candidates gated by anchor-membership + similarity ladder → batches of 100 resolved by ONE LLM call each (numbered questions, parsed back via regex; indices > records_length dropped) → merged pairs form a "same-as" graph whose connected components feed serialized `_merge_graph_nodes` → pagerank recomputed over the resolved graph.
**Invariant:** A pair is only sent to the LLM if it passes BOTH gates; a timed-out batch is skipped (counted as done) rather than failing the run; checkpoint keys normalize pair order (`sorted([sorted([a,b]) for a,b in pairs])`) so replay hits regardless of enumeration order; merges are serialized (see node-merge capsule).

## Get live surrounding code
**Retrieve:** (executed this pass)
```ts
await mcp.codebase_memory.search_graph({ project: "ragflow", query: "is_similarity candidate pairs resolution Levenshtein", fields: ["lines"] });
// rank-1 EntityResolution.is_similarity :275-289, rank-2 _resolve_candidate :199-243 + both direct tests ranked 3-4
```
**Probe:** `test/unit_test/rag/graphrag/test_entity_resolution.py` — `is_similarity("microsoft","microsfot") is True`, `("apple","orange") is False`, identical strings True (LLM-free constructor: `EntityResolution(llm_invoker=None)`).

## Verdict
Adopt the two-gate candidate filter and language-split similarity ladder, numbered-question batch prompting with index+verdict parsing, and per-batch checkpointed fail-forward semantics; adapt thresholds (Levenshtein ≤ len//2, CJK ≥0.8) and prompt wording to your domain; omit spaCy/NER variant specifics.
