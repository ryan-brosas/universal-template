<!-- capsule-v2 -->

# Deep-crawl recursion guard via ContextVar decorator — When the BFS strategy internally calls crawler.arun_many->arun for child URLs, what stops those calls from re-triggering deep crawling forever?

**Source:** crawl4ai Apache-2.0 `main@7e801521428ee12509994d39151006f64055ebe3`; Codebase Memory `ext-crawl4ai`. **Question:** When the BFS strategy internally calls crawler.arun_many->arun for child URLs, what stops those calls from re-triggering deep crawling forever?

## Instance-level decoration with ContextVar latch

**Path/Symbol:** `crawl4ai/deep_crawling/base_strategy.py:DeepCrawlDecorator.__call__ (17-43); wired at crawl4ai/async_webcrawler.py:170-171`.

**Signature:** `deep_crawl_active = ContextVar("deep_crawl_active", default=False); wrapped_arun(url, config=None, **kwargs)`.

**Data Shape:** Decorator wraps the BOUND arun at crawler construction: `self._deep_handler = DeepCrawlDecorator(self); self.arun = self._deep_handler(self.arun)` - every later caller (dispatcher, BFS level loops, user code) goes through the guarded wrapper.

### Decisive source
```python
async def wrapped_arun(url: str, config: CrawlerRunConfig = None, **kwargs):
            # If deep crawling is already active, call the original method to avoid recursion.
            if config and config.deep_crawl_strategy and not self.deep_crawl_active.get():
                token = self.deep_crawl_active.set(True)
                result_obj = await config.deep_crawl_strategy.arun(
                    crawler=self.crawler, start_url=url, config=config)
                if config.stream:
                    async def result_wrapper():
                        try:
                            async for result in result_obj:
                                yield result
                        finally:
                            self.deep_crawl_active.set(False)
                    return result_wrapper()
                else:
                    try:
                        return result_obj
                    finally:
                        self.deep_crawl_active.set(False)
            return await original_arun(url, config=config, **kwargs)
```

**Flow:** config carries a strategy? -> ContextVar False? -> set True -> delegate WHOLE traversal to strategy -> reset in finally (batch: around return; stream: generator's own finally so early consumer-close still resets) -> any NESTED arun during traversal sees True and falls through to the original single-URL arun. BFS reinforces defense-in-depth by cloning configs with deep_crawl_strategy=None before calling arun_many (see bfs-level-loop capsule).

**Invariant:** (1) Reset MUST sit in a finally/generator-finally - an exception mid-traversal leaving the flag set poisons every future deep crawl on that crawler; the dedicated regression suite pins exactly this. (2) ContextVars (not module booleans) make the guard task-local, so two crawls in different tasks don't cancel each other. (3) Decoration happens ONCE at __init__ via attribute assignment - replacing arun per-call would bypass the guard. CAVEAT: a second, experimental DeepCrawlDecorator lives in deep_crawling/crazy.py (list-stack ContextVar + traverse() API); the WIRED one is base_strategy's - deep_crawling/__init__ exports it and AsyncWebCrawler imports from the package root.

**Probe:** `tests/deep_crawling/test_deep_crawl_contextvar.py` (9 cases: flag true during crawl, false after batch/stream, reset-after-streaming-error, consumed-in-different-task, recursive-call prevention, concurrent streams)

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph '{"project": "ext-crawl4ai", "query": "DeepCrawlDecorator wrapped_arun deep_crawl_active", "limit": 5}'
```

## Verdict
Adopt the ContextVar guard + instance-attribute decoration pairing exactly; a module-level flag breaks under concurrent crawlers and decorating at call time misses the dispatcher's internal arun calls. Adapt strategy method names if you port a different traversal API. Omit the crazy.py experimental variant unless porting its bloom-filter frontier too - its ctxvar holds a LIST stack, not a bool, and its strategy API is traverse(), not arun().
