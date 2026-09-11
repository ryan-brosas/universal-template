<!-- capsule-v2 -->
# Audit orchestrator & shared result builder — how do 25+ sub-audits compose once for sync and async callers?

**Source:** GeoReady (Geo Optimizer) MIT `main@a7165be2`; Codebase Memory `ext-aeo-geo-optimizer-skill`. **Question:** How does one codebase serve sync CLI, async API, and MCP without divergent audit logic?

## _build_audit_result as the single composition point
**Path/Symbol:** `src/geo_optimizer/core/audit.py:_build_audit_result` (384–695), `run_full_audit` (698–896), `run_full_audit_async` (899–1098).
**Signature:** `_build_audit_result(base_url, robots, llms, schema, meta, content, http_status, page_size, soup=None, soup_clean=None, ...20 optional pre-computed sub-results...) -> AuditResult`.
**Data Shape:** every optional sub-result defaults to `None`; the builder substitutes an empty typed default (`SignalsResult()`, `BrandEntityResult()`, `PromptInjectionResult()`, ...) so consumers never see `None`.

### Decisive source
```python
# fix #285: compute soup_clean ONCE — script/style stripped — and hand it to
# every text-consuming sub-audit; avoids 3-4 re-parses (50–200 ms/page)
soup_clean = copy.deepcopy(soup)
for tag in soup_clean(["script", "style"]):
    tag.decompose()
...
# r is None, not "not r": requests.Response.__bool__ is .ok, so any 4xx/5xx is
# falsy and would be misreported as "Connection failed" (fix #330-class)
if err or r is None:
    ...
if r.status_code not in (200, 203):        # fix #337: name the HTTP error + WAF hint, skip analysis
    ...
# v4.7+ lazy fallbacks: pre-computed value WINS, else compute from soup, else empty default
if rag_chunk is not None:
    effective_rag_chunk = rag_chunk
elif soup is not None:
    from geo_optimizer.core.audit_rag import audit_rag_readiness
    effective_rag_chunk = audit_rag_readiness(soup, soup_clean)
else:
    effective_rag_chunk = RagChunkResult()
```

**Flow:** sync path fetches homepage → guards (`r is None`, status ∉ {200,203}) → builds soup + soup_clean → 7 sequential `fetch_url` calls for robots/llms/llms-full/.well-known/ai.txt//ai/*.json → runs DOM-only sub-audits → delegates to the SAME `_build_audit_result` as async. Async path swaps in one parallel `fetch_urls_async` batch and wraps only the genuinely-blocking CDN check in `asyncio.to_thread`. Plugin loading + citability run INSIDE the shared builder so both paths get them.
**Invariant:** The builder owns scoring/band/recommendations/plugins/citability; callers pass pre-computed sub-results or accept computed-from-soup fallbacks — adding a new audit means touching exactly three places: a new optional kwarg, its None-fallback ladder, and the `AuditResult(...)` constructor. X-Robots-Tag header handling must stay on BOTH paths (sync reads `r.headers`, async reads `r_home.headers`) — it's the one signal that lives outside any sub-audit.
**Probe:** `tests/test_audit_contract.py::test_audit_result_has_required_fields` + `tests/test_core.py::TestRunFullAudit::test_full_audit_url_normalization` (contract fixture pins required fields incl. `score_breakdown` with all 8 category keys).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aeo-geo-optimizer-skill", query: "_build_audit_result soup_clean orchestrator", limit: 5, fields: ["signature","name","file"] });
```

## Verdict
Adopt the single-shared-builder + empty-default-substitution pattern for multi-check pipelines; adapt which sub-audits are pre-computed vs lazy; omit the per-version comment archaeology (fix #NNN markers) when porting forward.
