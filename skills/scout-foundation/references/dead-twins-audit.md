<!-- capsule-v2 -->
# Dead twins + UI-reimplemented helpers — which "library" symbols must a porter NOT wire?

**Source:** Scout MIT `main@171503bf`; Codebase Memory `Scout`. **Question:** Which enrichment/stealth functions look load-bearing but are dead or shadowed, and what does the live twin actually do differently?

## Never-wired trio + the settings menu's divergent inline proxy test
**Path/Symbol:** `enrichment.py` `_domain_pattern_cache`/`_cache_lock` (:28-29 init, zero reads/writes after), `LeadEnricher.enrich_bulk` (:566-579, zero call sites); `stealth.py:test_proxy` (:115-125, zero call sites); live twin `scout.py:settings_menu` choice '4' (:950-986).
**Signature:** `test_proxy() -> bool` vs the UI's own httpx probe; `enrich_bulk(leads, max_workers=3) -> List[Dict]`.
**Data Shape:** dead-cache pair initialized but never touched — pattern prediction is stateless recomputation per call; `test_proxy` returns bool via requests+httpbin; UI twin returns rich console verdicts and prints the egress IP.

### Decisive source
```python
# scout.py settings choice '4' — does NOT call stealth.test_proxy:
from app.scrapers.stealth import get_proxy
px = get_proxy()
...
resp = _httpx.get('https://httpbin.org/ip', proxy=proxy_url, timeout=10, verify=False)
ip = resp.json().get('origin', '?')
console.print(f"[green]✓ Proxy works! IP: {ip}[/green]")
...
if free_enabled:
    from app.scrapers.stealth import _fetch_free_proxies   # reaches INTO stealth internals
    proxies = _fetch_free_proxies()
    for p in proxies[:3]:                                  # try up to 3 alternates
        ...
else:
    console.print("[red]All free proxies failed. Use a paid proxy.[/red]")  # for/else
```

**Flow (UI twin):** resolve current proxy via the ladder → no proxy = direct-connection check → proxy set = one httpx GET through it (`verify=False`, `proxy=` kwarg — note requests-style dicts would fail) → on failure with free tier on, pull the module cache and try up to 3 candidates → exhaustion message via for/else.
**Invariant:** THREE library symbols are decoys: `retry_request` (documented in `retry-semantics`), plus `test_proxy` and `enrich_bulk` — porting them as "the mechanism" wires code no user path executes. The REAL proxy test lives in the UI layer and diverges deliberately: httpx not requests, TLS verification OFF (free proxies break chains), IP echo instead of bool, and a free-tier fallback ladder that imports a private helper across module boundaries. The dead cache is equally instructive: someone planned memoized pattern detection, never finished, and left thread-safe-looking scaffolding — don't resurrect it.
**Probe:** no tests (zero-test repo). Deterministic probe: `grep -rn "test_proxy\|enrich_bulk" --include="*.py" .` → definitions only, zero call sites; `grep -n "_domain_pattern_cache" app/scrapers/enrichment.py` → exactly :28 (its lock sibling `_cache_lock` is :29 — pin both via `grep -n "_domain_pattern_cache\|_cache_lock" app/scrapers/enrichment.py`); `grep -n "verify=False" scout.py` pins both UI-probe sites (:966, :979).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Scout", query: "settings_menu test connection proxy httpbin", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the LESSON (audit call sites before wiring library helpers; UI-layer reimplementations often supersede them) and the working UI probe if you need a proxy health check; adapt its fallback depth and messaging; omit all four dead/shadowed symbols (`test_proxy`, `enrich_bulk`, `_domain_pattern_cache`+lock, `retry_request`) exactly as upstream did. Coverage caveat: pinned by source lines only.
