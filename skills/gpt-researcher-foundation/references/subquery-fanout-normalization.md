<!-- capsule-v2 -->
# Sub-query fan-out normalization — how is malformed planner JSON coerced into a safe sub-query list, and when does the original query rejoin it?

**Source:** gpt-researcher Apache-2.0 `main@5d84d2f5553e70a2765a8ff3a0d2672d60437ce8`; Codebase Memory `gpt-researcher`. **Question:** What shape must come out of the query planner no matter what the LLM returns, and who appends the original query?

## _normalize_sub_queries + generate_sub_queries fallback ladder
**Path/Symbol:** `gpt_researcher/actions/query_processing.py:6-34` (`_normalize_sub_queries`), `:82-155` (`generate_sub_queries`), `:157-214` (`plan_research_outline`).
**Signature:** `def _normalize_sub_queries(parsed: Any, fallback_query: str) -> List[str]`
**Data Shape:** Accepts list / dict (`queries`|`sub_queries`|`subQueries`|`items` keys, or single `query`) / bare string / None → always returns non-empty `list[str]` or `[fallback_query.strip()]`.

### Decisive source
```python
queries = [str(item).strip() for item in parsed if str(item).strip()]
if not queries and fallback_query.strip():
    return [fallback_query.strip()]
return queries
```

**Flow:** planner prompt asks for search queries with `max_iterations=cfg.max_iterations or 3` → strategic LLM call tries `max_tokens=None`; on failure retries with `cfg.strategic_token_limit` (issue #1022); on second failure falls back to the SMART model entirely → `json_repair.loads(response)` → `_normalize_sub_queries` → caller (`researcher.py:365-366`) appends the ORIGINAL query again **unless** `report_type == "subtopic_report"`.
**Invariant:** the returned list is never empty (crash-proof downstream `.append`/iteration), and a top-level researcher ALWAYS researches its own original query in addition to planned ones — dropping that append silently narrows coverage. Note for Python <3.13 porters: the module uses `List`/`Any` annotations ABOVE its typing import (line 6 vs 37) and only parses because annotations are lazy; keep import order sane if you reorganize.
**Probe:** `tests/test_sub_query_normalization.py::TestNormalizeSubQueries` (8 cases incl. none→fallback, blanks dropped); battery P04a/B4-B7 GREEN.
