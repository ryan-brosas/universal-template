<!-- capsule-v2 -->

# CacheMode decision context — Where do read/write cache decisions live and how do five modes map onto them without scattering ifs across the crawler?

**Source:** crawl4ai Apache-2.0 `main@7e801521428ee12509994d39151006f64055ebe3`; Codebase Memory `ext-crawl4ai`. **Question:** Where do read/write cache decisions live and how do five modes map onto them without scattering ifs across the crawler?

## Centralized predicates

**Path/Symbol:** `crawl4ai/cache_context.py:CacheContext.should_read/should_write (59-87) + _legacy_to_cache_mode (95-117)`.

**Signature:** `def __init__(self, url: str, cache_mode: CacheMode, always_bypass: bool = False); def should_read(self) -> bool; def should_write(self) -> bool`.

**Data Shape:** CacheMode in {ENABLED, DISABLED, READ_ONLY, WRITE_ONLY, BYPASS}. Context precomputes url classes: is_cacheable=(http|https|file://), is_web_url, is_local_file, is_raw_html=('raw:' prefix), display_url masks raw content as 'Raw HTML'.

### Decisive source
```python
def should_read(self) -> bool:
        if self.always_bypass or not self.is_cacheable:
            return False
        return self.cache_mode in [CacheMode.ENABLED, CacheMode.READ_ONLY]

    def should_write(self) -> bool:
        if self.always_bypass or not self.is_cacheable:
            return False
        return self.cache_mode in [CacheMode.ENABLED, CacheMode.WRITE_ONLY]
```

**Flow:** arun coerces cache_mode None->ENABLED then builds ONE CacheContext; every downstream decision asks should_read()/should_write() (read before fetch, write only `if cache_context.should_write() and not bool(cached_result)` after a live fetch). Legacy boolean flags collapse in strict precedence order: disable_cache->DISABLED; bypass_cache->BYPASS; no_cache_read+no_cache_write->DISABLED; no_cache_read alone->WRITE_ONLY; no_cache_write alone->READ_ONLY; else ENABLED.

**Invariant:** raw: URLs are NEVER cacheable (prefix list excludes them) yet ARE processable - cacheability and processability are orthogonal. WRITE_ONLY still reads nothing but writes fresh results; BYPASS differs from DISABLED only in intent-documentation (both block read+write via the same predicate gates since neither is in the read/write membership lists).

**Probe:** `tests/test_config_defaults.py` + `tests/general/` cache-mode unit coverage (mode->predicate mapping)

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph '{"project": "ext-crawl4ai", "query": "CacheContext CacheMode should_read", "limit": 5}'
```

## Verdict
Adopt the two-predicate truth table and the prefix-based cacheability classes verbatim - READ_ONLY/WRITE_ONLY asymmetry and raw:-never-cacheable are the contract. Adapt the legacy-flag precedence if your host has different deprecated knobs; keep DISABLED > BYPASS ordering (they differ: DISABLED also blocks explicit-mode reads).
