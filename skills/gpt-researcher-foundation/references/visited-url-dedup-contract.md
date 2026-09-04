<!-- capsule-v2 -->
# Visited-URL dedup contract — which passes share visited_urls, and why must conduct_research NOT clear it?

**Source:** gpt-researcher Apache-2.0 `main@5d84d2f5553e70a2765a8ff3a0d2672d60437ce8`; Codebase Memory `gpt-researcher`. **Question:** Where do URL dedup semantics live across parent/subtopic/hybrid researchers, and what breaks if a porter "cleans up" the set?

## Shared set across researcher generations
**Path/Symbol:** `gpt_researcher/skills/researcher.py:108-111` (deliberate no-clear comment), `:801-822` (`_get_new_urls` claim loop), `:171-183` (hybrid concurrent gather), `agent.py:161` (`visited_urls or set()` constructor default).
**Signature:** `async def _get_new_urls(self, url_set_input) -> list[str]` — claims URLs by adding to the shared set BEFORE scraping.
**Data Shape:** `visited_urls: set[str]` passed BY REFERENCE into subtopic and deep-research child constructors; `_get_new_urls` returns only unclaimed URLs.

### Decisive source
```python
# Note: visited_urls is deliberately NOT cleared here. It may be
# shared with a parent researcher (e.g. detailed reports pass their
# accumulated URLs into each subtopic researcher) so that already
# scraped URLs are not fetched again.
...
docs_context, web_context = await asyncio.gather(
    self._get_context_by_web_search(..., document_data, ...),
    self._get_context_by_web_search(..., [], ...),
)
# The local-docs pass and the web pass are independent... visited_urls still dedupes across both.
```

**Flow:** report generators (detailed/subtopic/deep research) thread one set through every child → each pass claims new URLs under iteration → scraper receives only never-scraped links → hybrid's two CONCURRENT passes rely on set membership as the dedupe primitive.
**Invariant:** clearing at pass start re-fetches everything in multi-report flows; conversely the set is a shared-mutable contract — deep research RETURNS it wholesale (`self.researcher.visited_urls = results['visited_urls']`) so callers see accumulated history.
**Probe:** battery P11e GREEN ("deliberately NOT cleared" comment pin ×1). Coverage caveat: behavior pinned by source comment + call-graph, no direct unit test.
