<!-- capsule-v2 -->
# Deep research descent budget — how do breadth, depth, and concurrency bound the recursive research tree?

**Source:** gpt-researcher Apache-2.0 `main@5d84d2f5553e70a2765a8ff3a0d2672d60437ce8`; Codebase Memory `gpt-researcher`. **Question:** What are the exact recursion mechanics of DeepResearchSkill.deep_research, and which state propagates into child researchers?

## Recursive breadth-halving descent
**Path/Symbol:** `gpt_researcher/skills/deep_research.py:377-575` (`deep_research`), `:425-481` (`process_query` closure), `:531-559` (recursion arm), `:244-257` (config defaults breadth=4, depth=2, concurrency=2).
**Signature:** `async def deep_research(self, query, breadth, depth, learnings=None, citations=None, visited_urls=None, on_progress=None) -> Dict[str, Any]`
**Data Shape:** Returns `{learnings: deduped list, visited_urls, citations: {learning→url}, context: word-trimmed list, sources}`. SERP queries are `{query, researchGoal}` pairs.

### Decisive source
```python
semaphore = asyncio.Semaphore(self.concurrency_limit)
...
if depth > 1:
    new_breadth = max(2, breadth // 2)
    new_depth = depth - 1
    next_query = f"""
    Previous research goal: {result['researchGoal']}
    Follow-up questions: {' '.join(result['followUpQuestions'])}
    """
    deeper_results = await self.deep_research(next_query, new_breadth, new_depth,
                                              learnings=all_learnings, ...)
```

**Flow:** `run()` auto-answers its own follow-up questions ("Automatically proceeding with research") → per level generate `breadth` queries with goals → concurrent branches each spawn a CHILD GPTResearcher (report_type=ResearchReport, Web source) sharing `visited_urls`, `headers`, `websocket`, MCP configs/strategy → extract learnings+citations via LLM → recurse per successful branch while depth>1 → final context trimmed to MAX_CONTEXT_WORDS=25000.
**Invariant:** recursion happens INSIDE the result-collection loop, so sibling branches at one level run under ONE semaphore while their subtrees serialize after them; failed branches return None and are filtered; #1579 guard stops descent when EVERY branch at a level failed (prevents infinite follow-up generation from empty learnings).
**Probe:** battery P18b-c GREEN for the budget fold; #1579 all-failed stop pinned by source :496-504.
