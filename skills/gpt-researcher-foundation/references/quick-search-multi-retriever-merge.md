<!-- capsule-v2 -->
# Quick-search multi-retriever merge — how does one-shot search fan out across retrievers without a failing provider aborting the batch?

**Source:** gpt-researcher Apache-2.0 `main@5d84d2f5553e70a2765a8ff3a0d2672d60437ce8`; Codebase Memory `gpt-researcher`. **Question:** How do you query every configured retriever concurrently, merge results, and keep one provider's exception from killing the search?

## GPTResearcher._search_all_retrievers + quick_search switch
**Path/Symbol:** `gpt_researcher/agent.py:572-606` (`_search_all_retrievers`), `:519-570` (`quick_search`).
**Signature:** `async def _search_all_retrievers(self, query: str, query_domains: list[str] = None) -> list[dict[str, Any]]`; `async def quick_search(self, query, query_domains=None, aggregated_summary=False, all_retrievers=False) -> list[Any] | str`.
**Data Shape:** Retriever records are heterogeneous key-sets: primary keys `href`/`body`, alternate `url`/`content`; merged output preserves first-seen order per URL.

### Decisive source
```python
results = await asyncio.gather(*tasks, return_exceptions=True)

merged: list[dict[str, Any]] = []
seen_urls: set[str] = set()
for result in results:
    if isinstance(result, Exception) or not result:
        continue                       # failing retriever is SKIPPED, not fatal
    for item in result:
        url = item.get("url") or item.get("href") or ""
        if url and url in seen_urls:
            continue
        if url:
            seen_urls.add(url)
        merged.append(item)
```

**Flow:** `quick_search` picks `_search_all_retrievers` only when `all_retrievers=True AND len(retrievers) > 1`, else the single primary retriever (`self.retrievers[0]`) for backward compatibility → summary mode formats `[i] title: body (url)` lines using the SAME dual-key fallbacks (`result.get("body") or result.get("content")`, `result.get("href") or result.get("url")`) and synthesizes an answer via smart-LLM with `smart_token_limit`.
**Invariant:** exceptions from individual retrievers are swallowed by the gather (return_exceptions=True) and filtered — availability degradation beats partial failure; dedup treats `url` and `href` as aliases of ONE identity because different retriever families use different keys; records with NO url key always append (can't be deduped). The >1-retrievers guard means single-retriever configs never pay gather overhead.
**Probe:** `tests/test_quick_search.py` pins all three invariants with pure mocks (`get_search_results` AsyncMock, `MagicMock(__name__=...)` retrievers, patched embeddings — no live keys): `test_quick_search_all_retrievers_merges_and_dedups` :47-71 (dup href appears once, 3 results), `test_quick_search_all_retrievers_skips_failing_retriever` :75-90 (RuntimeError swallowed, healthy half returned), `test_quick_search_single_retriever_ignores_all_flag` :94-106 (one retriever ⇒ primary path). In-lane EXECUTION remains blocked (missing aiofiles deps; read-only checkout) but the pins are upstream unit truth, not source-read inference.
**Coverage:** check_index_coverage `no_recorded_issue`/`metadata_match` for agent.py @ gen 2026-08-26T01:42:19Z.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "gpt-researcher", query: "_search_all_retrievers quick_search merged seen_urls", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the skip-don't-fail gather, the dual-key dedup identity, and the backward-compatible single-retriever short-circuit. Adapt record schemas to your retriever set (keep an explicit alias table). Omit the prompt-side quick-summary formatting unless porting the CLI surface.
