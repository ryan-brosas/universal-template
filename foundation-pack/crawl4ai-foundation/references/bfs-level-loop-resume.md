<!-- capsule-v2 -->

# BFS level loop with crash-resumable state — How does a level-synchronous deep crawl survive restarts, and why do batch and stream modes mark visited differently?

**Source:** crawl4ai Apache-2.0 `main@7e801521428ee12509994d39151006f64055ebe3`; Codebase Memory `ext-crawl4ai`. **Question:** How does a level-synchronous deep crawl survive restarts, and why do batch and stream modes mark visited differently?

## Level loop + resume snapshot

**Path/Symbol:** `crawl4ai/deep_crawling/bfs_strategy.py:BFSDeepCrawlStrategy._arun_batch (207-301) / _arun_stream (303-401)`.

**Signature:** `current_level: List[Tuple[str, Optional[str]]]  # (url, parent_url); depths: Dict[str, int]; resume keys: visited/pending[{url,parent_url}]/depths/pages_crawled`.

**Data Shape:** Results get result.metadata['depth'], result.metadata['parent_url'], and (scored links) metadata['score']. State dict adds strategy_type='bfs' and cancelled flag.

### Decisive source
```python
# Clone the config to disable deep crawling recursion and enforce batch mode.
            batch_config = config.clone(deep_crawl_strategy=None, stream=False)
            batch_results = await crawler.arun_many(urls=urls, config=batch_config)
            ...
                if result.success:
                    self._pages_crawled += 1
                    await self.link_discovery(result, url, depth, visited, next_level, depths)
                    if self._on_state_change:
                        state = {"strategy_type": "bfs",
                                 "visited": list(visited),
                                 "pending": [{"url": u, "parent_url": p} for u, p in next_level],
                                 "depths": depths,
                                 "pages_crawled": self._pages_crawled,
                                 "cancelled": self._cancel_event.is_set()}
                        await self._on_state_change(state)
            current_level = next_level
```

**Flow:** resume_state restores visited/pending/depths/pages_crawled instead of seeding start_url -> per level: check max_pages + cancellation -> arun_many over the level with cloned config -> tag depth/parent -> SUCCESSFUL results increment _pages_crawled and run link_discovery -> state callback fires PER URL -> next_level becomes current_level -> cancelled exits flush a final state with pending=current_level. Stream variant yields per result and pre-adds the whole level to visited BEFORE crawling.

**Invariant:** (1) The clone stripping deep_crawl_strategy is what makes the ContextVar guard belt-and-suspenders: even a missed reset cannot recurse. (2) Only successful crawls count toward max_pages and spawn discovery - failures consume neither budget nor frontier expansion. (3) Batch marks visited per-link inside link_discovery AFTER filtering/scoring; stream marks the entire level UP FRONT (visited.update(urls)) - so an interrupted stream records URLs as visited that batch wouldn't. (4) Zero-results-for-level is logged, NOT fatal, and those URLs count as visited-but-unbudgeted (stream path) to avoid infinite loops. (5) should_cancel callback failures fail OPEN (log + continue).

**Probe:** `tests/deep_crawling/test_deep_crawl_resume.py` (state export/import round-trips) + `test_deep_crawl_resume_integration.py` + `test_deep_crawl_cancellation.py`

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph '{"project": "ext-crawl4ai", "query": "BFSDeepCrawlStrategy link_discovery arun_batch", "limit": 5}'
```

## Verdict
Adopt: config.clone(deep_crawl_strategy=None, ...) at every delegation, success-gated counters/discovery, the resume-state key set, and per-level cancel checks. Adapt scoring hooks. Watch the batch-vs-stream visited-timing divergence if you rely on visited as a dedupe export. Omit DFS/BFF variants here - same contract family, separate strategies (bff pops highest-score via heap; dfs uses an explicit stack).
