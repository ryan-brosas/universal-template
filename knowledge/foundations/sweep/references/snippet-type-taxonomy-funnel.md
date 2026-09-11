<!-- capsule-v2 -->
# Snippet type taxonomy — how do you route retrieved files into per-type budgets without a classifier?

**Source:** sweep (Apache-2.0) `main@a8b8b67bda4f`; Codebase Memory `sweep`. **Question:** How can path-shaped pattern tables give each file category (source/tests/docs/tools/deps) its own retrieval budget, and where does junk actually get excluded?

## separate_snippets_by_type first-match table + per-type tuning dicts
**Path/Symbol:** `sweepai/utils/ticket_utils.py:code_snippet_separation_features` (:36–67), `separate_snippets_by_type` (:103–113), tuning tables `type_to_percentile_floor`/`type_to_score_floor`/`type_to_result_count`/`rerank_count` (:71–101); container `sweepai/dataclasses/separatedsnippets.py:SeparatedSnippets` (whole).
**Signature:** `separate_snippets_by_type(snippets: list[Snippet]) -> SeparatedSnippets`.
**Data Shape:** Ordered dict of 5 categories; each rule set = `{prefix: [...], suffix: [...], substring: [...]}` matched against `snippet.file_path`; unmatched ⇒ `source`. Iteration yields `(type_name, list)` pairs in fixed order source→tests→tools→dependencies→docs, never junk.

### Decisive source
```python
for type_name, separation in code_snippet_separation_features.items():
    if any(snippet.file_path.startswith(prefix) for prefix in separation["prefix"]) or \
       any(snippet.file_path.endswith(suffix) ...) or any(substring in snippet.file_path ...):
        separated_snippets.add_snippet(snippet, type_name); break
else:
    separated_snippets.add_snippet(snippet, "source")

# separatedsnippets.py __iter__ — the ONLY junk exclusion mechanism:
yield "source", self.source
...
# yield "junk", self.junk
# we won't yield junk
```

**Flow:** every retrieved snippet gets exactly one type (first matching category wins, dict order matters) → later funnel stages look up that type in four parallel tuning dicts: percentile floor (.15 source vs .3 others), absolute score floor (0.0 source, .2 docs), result count (30/15/5), and rerank budget (50 source … 10 tools/deps) — so cheap heuristics decide how much reranker spend each category earns.
**Invariant:** Junk is excluded STRUCTURALLY by `__iter__` never yielding it, not by deletion. Consequence: the guard at `multi_prep_snippets:337–338` (`if "junk" in separated_snippets: override_list("junk", [])`) is dead code — `"junk" in obj` falls back to iteration-comparison against `(name, list)` tuples and can never be True. A port that "fixes" this by yielding junk would start feeding lockfiles/node_modules to the LLM.
**Probe:** No offline unit test covers the separation (coverage caveat). Deterministic probes at pin: `grep -c 'yield "' sweepai/dataclasses/separatedsnippets.py` → 6 (five live yields + the commented-out junk yield); `grep -c '"junk"' sweepai/utils/ticket_utils.py` → 3 (taxonomy key + dead guard ×2).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "sweep", query: "separate snippets type tools junk dependencies docs tests", limit: 10 });
// executed at pin: separate_snippets_by_type ticket_utils.py 103-113;
// process_snippets :290-294; multi_prep_snippets :297-419 in same group
```

## Verdict
Adopt ordered path-pattern taxonomy with first-match-wins plus per-category budget/floor tables as a zero-cost router before any model-based ranking, and structural exclusion of noise categories via a filtered iterator. Adapt the pattern vocabularies to your ecosystem. Omit Sweep's AnalyzeSnippetAgent second-stage filter unless you have the LLM budget for it.
