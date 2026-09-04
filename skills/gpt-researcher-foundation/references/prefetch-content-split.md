<!-- capsule-v2 -->
# Prefetched-content split — when does a retriever result skip the scraper entirely, and in what order do scraped and prefetched contexts merge?

**Source:** gpt-researcher Apache-2.0 `main@5d84d2f5553e70a2765a8ff3a0d2672d60437ce8`; Codebase Memory `gpt-researcher`. **Question:** Which retriever payloads count as "already fetched full pages", and how must a porter merge them with freshly scraped ones?

## _search_relevant_source_urls raw_content gate + merge order
**Path/Symbol:** `gpt_researcher/skills/researcher.py:824-870` (`_search_relevant_source_urls`), `:872-907` (`_scrape_data_by_urls`).
**Signature:** `async def _search_relevant_source_urls(self, query, query_domains: list | None = None) -> tuple[list[str], list[dict]]`.
**Data Shape:** Returns `(new_search_urls, prefetched_content)`; prefetched items are exactly `{url, raw_content}`; search runs via `asyncio.to_thread(retriever.search, max_results=cfg.max_search_results_per_query)` because retriever searches are blocking HTTP.

### Decisive source
```python
# researcher.py:849-862 — ONLY raw_content signals a fetched page:
for result in search_results:
    url = result.get("href") or result.get("url")
    raw_content = result.get("raw_content")
    if url and raw_content and len(raw_content) > 100:
        # Only raw_content signals that a retriever already fetched the full page.
        # body is snippet-sized text for most web retrievers and still needs scraping.
        prefetched_content.append({"url": url, "raw_content": raw_content})
        self.researcher.add_research_sources([{"url": url}])
    elif url:
        new_search_urls.append(url)
...
new_search_urls = await self._get_new_urls(new_search_urls)
random.shuffle(new_search_urls)
```
```python
# researcher.py:898-902 — scrape first, THEN extend with prefetched:
scraped_content = await self.researcher.scraper_manager.browse_urls(new_search_urls)
scraped_content.extend(prefetched_content)
```

**Flow:** every configured non-MCP retriever is instantiated per sub-query (MCP classes skipped — they return no scrapable URLs) → results split at the `raw_content >100 chars` boundary → URL half goes through visited-URL claim + random shuffle → browse_urls → prefetched half appended AFTER scraped items → optional vector_store.load over the merged list.
**Invariant:** `body` is NEVER sufficient to skip scraping even when long; only `raw_content` proves a full fetch. Prefetched URLs bypass `_get_new_urls` claim (they enter research_sources directly) but still reach compression. The shuffle spreads scraper load across domains between sub-queries; MCP retrievers must stay excluded or URL-less tool results would pollute the scrape queue.
**Probe:** `tests/test_research_conductor_retrieval.py` ×2 executed-read GREEN pins both halves: snippet-only retriever yields `urls=[one,two], prefetched=[]`; full-content retriever yields `urls=[], prefetched=[{url, raw_content:"C"*500}]`. Runner BLOCKED in-lane (missing aiofiles; read-only checkout) — test bodies verified line-exact instead.
**Coverage:** check_index_coverage `no_recorded_issue`/`metadata_match` for skills/researcher.py @ gen 2026-08-26T01:42:19Z.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "gpt-researcher", query: "_search_relevant_source_urls prefetched raw_content", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the split predicate and merge order verbatim — dropping either re-scrapes full pages or loses retriever-only corpora (PubMed Central-style). Adapt the >100 threshold to your retrievers' minimum viable page size. Omit gpt-researcher's specific retriever class table; keep the "skip MCP in URL collection" rule.
