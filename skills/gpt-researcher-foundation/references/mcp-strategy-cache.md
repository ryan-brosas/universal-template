<!-- capsule-v2 -->
# MCP strategy cache — how do fast/deep/disabled strategies avoid paying for the same MCP research twice per pass?

**Source:** gpt-researcher Apache-2.0 `main@5d84d2f5553e70a2765a8ff3a0d2672d60437ce8`; Codebase Memory `gpt-researcher`. **Question:** Where is MCP research executed once vs. per-sub-query, and what guards the cache under concurrent passes?

## Strategy resolution + one-shot cache + Tavily dedupe
**Path/Symbol:** `gpt_researcher/skills/researcher.py:307-358` (cache fill under `_mcp_cache_lock`), `:398-422` (`_get_mcp_strategy`), `:480-505` (`_tavily_mcp_redundant_with_direct`), `:508-651` (`_process_sub_query` strategy arms).
**Signature:** `self._mcp_results_cache: list | None`; `async with self._mcp_cache_lock:` guards population; `self._mcp_query_count` reserved for balanced mode.
**Data Shape:** MCP context entries are `{content, url, title, query, source_type:"mcp"}` dicts. Strategy values: `"fast"` (default) / `"deep"` / `"disabled"`, resolved instance → config → "fast".

### Decisive source
```python
async with self._mcp_cache_lock:
    if mcp_retrievers and self._mcp_results_cache is None:
        if mcp_strategy == "fast":
            mcp_context = await self._execute_mcp_research_for_queries([query], mcp_retrievers)
            self._mcp_results_cache = mcp_context
...
# per sub-query:
elif mcp_strategy == "fast" and self._mcp_results_cache is not None:
    mcp_context = self._mcp_results_cache.copy()   # reuse; never re-call
elif mcp_strategy == "deep":
    mcp_context = await self._execute_mcp_research_for_queries([sub_query], mcp_retrievers)
```

**Flow:** hybrid mode runs two web-search passes concurrently — the lock makes exactly ONE populate the cache → each sub-query copies cached results in fast mode or re-executes per-query in deep mode → disabled skips entirely → unknown strategies warn and degrade to fast.
**Invariant:** Tavily-dual-path guard: if every configured MCP server's name/args/command blob contains "tavily" AND direct `TavilySearch` is also active, MCP retrievers are dropped for the sub-query (#1875 — same API paid twice plus tool-selection cost). Cache reuse must `.copy()` because consumers mutate lists.
**Probe:** battery P11c-e GREEN (`async with self\._mcp_cache_lock:` ×1; helper wired ×2 call+def; "deliberately NOT cleared" comment pin). Coverage caveat: no dedicated upstream test for the lock path.
