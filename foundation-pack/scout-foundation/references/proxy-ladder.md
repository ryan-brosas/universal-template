<!-- capsule-v2 -->
# Proxy ladder — how do three proxy tiers collapse into one Optional[str] with per-client shaping?

**Source:** Scout MIT `main@171503bf`; Codebase Memory `Scout`. **Question:** How does every scraper share one egress policy (custom URL → rotating file → free-proxy pool) without each platform knowing the tier logic?

## Priority ladder + three shaped accessors
**Path/Symbol:** `app/scrapers/stealth.py:get_proxy` (:67-84), `get_httpx_proxy` (:87-93), `get_requests_proxies` (:96-102), `proxy_status` (:105-112), `_fetch_free_proxies` (:37-64).
**Signature:** `get_proxy() -> str | None` (raw); `get_httpx_proxy() -> str | None` (scheme-prefixed); `get_requests_proxies() -> dict | None` (`{"http": p, "https": p}`).
**Data Shape:** env keys in strict order: `SCOUT_PROXY` → `SCOUT_PROXY_FILE` (one proxy per line, `#` comments skipped) → `SCOUT_FREE_PROXY ∈ {'1','true','yes'}`; free tier cached module-globally for `_FREE_PROXY_TTL = 300`s.

### Decisive source
```python
def get_proxy():
    proxy = os.environ.get('SCOUT_PROXY')
    if proxy: return proxy
    proxy_file = os.environ.get('SCOUT_PROXY_FILE')
    if proxy_file and os.path.exists(proxy_file):
        proxies = [l.strip() for l in open(proxy_file) if l.strip() and not l.startswith('#')]
        if proxies:
            return random.choice(proxies)          # rotation happens HERE, per call
    if os.environ.get('SCOUT_FREE_PROXY','').lower() in ('1','true','yes'):
        free_proxies = _fetch_free_proxies()
        if free_proxies: return random.choice(free_proxies)
    return None

def get_requests_proxies():
    ...
    return {'http': proxy, 'https': proxy}
```

**Flow:** every outbound call site asks afresh; file/free tiers rotate by `random.choice` *per request*, so a batch naturally spreads across the pool. Free-tier fetch wraps `fp.FreeProxy(timeout=1, rand=True, anonym=True)` in a 5-try loop and only caches non-empty results. `proxy_status()` re-derives the same ladder for UI display ('custom'/'file'/'free'/'none') — it never reads state, only env, so header and behavior can't disagree.
**Invariant:** callers must use the accessor matching their HTTP client — requests takes the dict, httpx takes the scheme-prefixed string (`http://` is prepended when missing because both libraries reject bare `host:port`); raw `get_proxy()` output fed directly to either client is the classic porting bug. The ladder short-circuits: an empty `SCOUT_PROXY=""` set-but-empty value is falsy and correctly falls through.
**Probe:** no direct test (zero-test repo). Deterministic probe: `grep -n "get_requests_proxies\|get_httpx_proxy" app/scrapers/*.py` shows every call site choosing the right shape per client (requests-dict: instagram/github/pinterest/twitch/youtube×2; httpx-string: tiktok only — linkedin imports `get_httpx_proxy` but NEVER calls it, its `httpx.Client`s in `validate_cookie`/`_get_session` run proxy-less, a dead import a porter should NOT copy; enrichment uses NO proxy at all); graph retrieval resolves `Scout.app.scrapers.stealth.get_proxy`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Scout", query: "get_proxy SCOUT_PROXY free", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the env-ladder + per-call random rotation + client-shaped accessor split as a complete portable egress primitive (~90 lines); adapt TTLs, provider, and env prefixes; omit `retry_request` (dead code upstream — see retry-semantics capsule) and the settings-menu proxy tester. Coverage caveat: pinned by source lines only.
