<!-- capsule-v2 -->
# Empty-descent UnboundLocalError — which early return in deep_research crashes on its own locals?

**Source:** gpt-researcher Apache-2.0 `main@5d84d2f5553e70a2765a8ff3a0d2672d60437ce8`; Codebase Memory `gpt-researcher`. **Question:** What happens when the query generator produces zero SERP queries at some recursion level, and what must a porter fix before relying on this path?

## Return-before-assignment defect
**Path/Symbol:** `gpt_researcher/skills/deep_research.py:406-414` (early return), `:416-420` (the assignments it reads).
**Signature:** inside `async def deep_research(...)` — the guard `if not serp_queries:` at :406.
**Data Shape:** The dict literal references five `all_*` names; four of them (`all_learnings`, `all_citations`, `all_visited_urls`, `all_context`) plus `all_sources` are first bound FOURTEEN lines LATER.

### Decisive source
```python
progress.total_queries = len(serp_queries)
if not serp_queries:
    logger.warning("Deep research generated zero search queries; stopping descent.")
    return {
        'learnings': all_learnings,        # :409  ← NOT YET BOUND
        'visited_urls': all_visited_urls,
        'citations': all_citations,
        'context': all_context,
        'sources': all_sources,
    }                                      # → UnboundLocalError, every time

all_learnings = learnings.copy()           # :416  ← actual binding site
```

**Flow:** any level where the strategic LLM yields zero parseable queries (degraded provider, over-filtered parser) enters the guard → Python evaluates the dict → `UnboundLocalError: local variable 'all_learnings' referenced before assignment` instead of the intended graceful stop. The SECOND early-return (:505-511, all-branches-failed #1579 guard) is CORRECT because it sits after the assignments.
**Invariant (for porters):** move the `all_*` initializations ABOVE the zero-query guard; until then treat "generator returned nothing" as a crash path, not a clean-stop path. Upstream's test file covers the parsers and trim fold but NOT this branch.
**Probe:** battery P01a-c GREEN — two `'learnings': all_learnings,` sites at lines [409, 506]; assignment :416 AFTER ret1:409; guard :406 precedes assignment.
