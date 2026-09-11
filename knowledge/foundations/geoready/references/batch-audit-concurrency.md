<!-- capsule-v2 -->
# Batch audit concurrency — semaphore, per-URL timeout, priority selection, graceful async degradation

**Source:** GeoReady (Geo Optimizer) MIT `main@a7165be2`; Codebase Memory `ext-aeo-geo-optimizer-skill`. **Question:** How do you audit 50 sitemap URLs concurrently without one hang or exception killing the batch?

## Semaphore + wait_for + per-page error capture
**Path/Symbol:** `src/geo_optimizer/core/batch_audit.py:run_batch_audit_async` (36–71), `_select_urls` (74–87), `_audit_urls` (90–112), `_aggregate_batch_result` (150+).
**Signature:** `run_batch_audit(sitemap_url, *, use_cache=False, project_config=None, max_urls=50, concurrency=5) -> BatchAuditResult`.
**Data Shape:** `BatchAuditPageResult(url, score, band, error…)`; aggregate carries `discovered_urls`, per-page list, averaged breakdown (`_average_breakdowns`), top/bottom pages (limit 5).

### Decisive source
```python
async def _worker(url: str) -> BatchAuditPageResult:
    async with semaphore:
        # Fix H-2: per-URL timeout prevents a single hanging URL from blocking the batch
        try:
            return await asyncio.wait_for(
                _audit_single_url(url, use_cache=use_cache, project_config=project_config),
                timeout=AUDIT_TIMEOUT_SECONDS,
            )
        except asyncio.TimeoutError:
            result = AuditResult(url=url, error=f"Timeout ({AUDIT_TIMEOUT_SECONDS}s)", band="critical")
            return _summarize_audit_result(result)

# gap #6: higher-priority pages audited first when max_urls forces a cutoff
sorted_entries = sorted(sitemap_entries, key=lambda e: getattr(e, "priority", 0.5), reverse=True)
```

**Flow:** validate args (`max_urls>0`, `concurrency>0` raise) → sitemap fetch via `asyncio.to_thread(fetch_sitemap, …)` → dedupe + priority-descend selection to `max_urls` → gather workers under `Semaphore(concurrency)` → each worker picks the async path when httpx exists and cache is off, else threads the sync audit (`asyncio.to_thread(run_full_audit, …)`) → exceptions become `error=` AuditResults with band critical, NEVER propagate → aggregate averages category breakdowns across pages.
**Invariant:** Every page produces a row even on timeout/exception — the aggregate is total over selected URLs by construction; the sync fallback keeps batches working in non-async runtimes at the cost of thread-pool parallelism. Selection order matters because the URL cap is a quality decision, not arbitrary.
**Probe:** `tests/test_batch_audit.py::test_batch_selects_priority_urls` (+ aggregation tests; `PYTHONPATH=src pytest tests/test_batch_audit.py -q` green at pin).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aeo-geo-optimizer-skill", query: "run_batch_audit semaphore wait_for", limit: 5, fields: ["signature","name","file"] });
```

## Verdict
Adopt bounded-concurrency + hard-per-item-timeout + error-as-row for any fan-out crawler/auditor; adapt limits; omit the httpx detection if your env guarantees async.
