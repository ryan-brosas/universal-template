<!-- capsule-v2 -->
# Mind-map intent placement — where does a new fact go in an LLM-maintained hierarchy, and when can insertion run in parallel?

**Source:** storm MIT `main@fb951af7`; Codebase Memory `storm`. **Question:** How do you place retrieved information into a growing topic tree using an LLM navigator, and why does the concurrency model flip with one boolean?

## Embedding-ranked candidate choice, then layer-by-layer LM navigation
**Path/Symbol:** `knowledge_storm/collaborative_storm/modules/information_insertion_module.py:InsertInformationModule` — `forward` (:221-313), `choose_candidate_from_embedding_ranking` (:175-211), `layer_by_layer_navigation_placement` (:108-147); expansion twin `ExpandNodeModule._expand_node` (:391-413).
**Signature:** `forward(knowledge_base, information: Union[Information, List[Information]], allow_create_new_node=False, max_thread=5, insert_root=None, skip_candidate_from_embedding=False)`.
**Data Shape:** Intent key = `(info.meta["question"], info.meta["query"])`; placement = `" -> "`-joined node path; per-intent result may be `None` (insert skipped).

### Decisive source
```python
if not allow_create_new_node:
    # use multi thread as knowledge base structure does not change
    with ThreadPoolExecutor(max_workers=max_thread) as executor: ...
else:
    # use sequential insert as knowledge base structure might change
    for question, query in intent_to_placement_dict:
        (encoded_outlines, outlines,) = knowledge_base.get_knowledge_base_structure_embedding(root=insert_root)
        _, placement_prediction = process_intent(question=question, query=query)
```

**Flow:** Info is grouped by intent so identical (question, query) pairs navigate once. Per intent: FIRST try embedding ranking — encode `"question, query"`, cosine-rank all node paths, take top-N candidates (the call site passes 8 although the signature default reads 5), show them numbered to the LM which answers `"Best placement: [k]"`; the 1-based index selects into the RANKED list; any parse failure returns None. FALLBACK is layer-by-layer navigation: an unbounded while-loop asking a ChainOfThought module at each node for `insert` / `step: [child]` / `create: [child]`, stepping raises ValueError on unknown children, `create` appends the name only when `allow_create_new_node` else records an "attempt to create" note. Placement then resolves via `insert_information(missing_node_handling="raise error" if not allow_create_new_node else "create")`. Expansion reuses the same module: when a node's content set passes `node_expansion_trigger_count`, LLM subsection names are created, the node's content set is RESET, and its info re-inserted under the new subtree with creation disabled.
**Invariant:** (1) The parallel/sequential split is correctness, not optimization: candidate-ranking navigates against a FROZEN structure snapshot, so it must never run concurrently while creates mutate what the next intent should see — hence sequential mode re-fetches structure embeddings per intent. (2) Candidate index k is 1-based into the ranked candidate list, and bounds-checked against `sorted_candidates` before use (:206). (3) Failed placements return None and the info is silently skipped (`insert_info_to_kb` no-ops on None) — partial inserts are invisible without counting. (4) `_expand_node` clears `node.content = set()` BEFORE re-insertion; keeping the old set would double-cite every item.
**Probe:** byte-pins executed this pass — :246 call-site `top_N_candidates=8` vs :181 signature default `5`, :201-205 "Best placement:" trim + `selected_index - 1`, :263-265 missing_node_handling ternary, :297 comment + :298-306 sequential re-embed loop, :406 `node.content = set()` reset. All line-exact.
**Coverage caveat:** file checked `no_recorded_issue` @ gen 2026-08-25T20:09:07Z.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "storm", query: "InsertInformationModule choose_candidate_from_embedding_ranking layer_by_layer_navigation_placement", limit: 10 });
```

## Verdict
Adopt the two-stage placement (cheap vector shortlist → structured LM decision) plus the frozen-snapshot concurrency rule for any LLM-curated tree; adapt candidate counts and nav grammar; omit nothing on the reset-and-reinsert expansion order and None-placement accounting — both are silent-corruption traps.
