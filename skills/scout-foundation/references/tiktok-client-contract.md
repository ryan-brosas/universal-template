<!-- capsule-v2 -->
# TikTok client contract — why does the one httpx-based platform reuse a module-global client and what do its typed errors decide?

**Source:** Scout MIT `main@171503bf8c56d61fd6462ff08c557ec0b7fafa34`; Codebase Memory `Scout`. **Question:** How is the shared egress policy attached to an httpx client, and how does the fetch layer's error typing interact with the batch loop's fatal-vs-skip contract?

## Module-singleton client + full browser header set + typed-error swallow ladder

**Path/Symbol:** `app/scrapers/tiktok.py` whole (102 L) — `_get_client` (:17-22), `_build_headers` (:25-36), `scrape_tiktok_profile` (:39-102).

**Signature:** `_get_client() -> httpx.Client`; `_build_headers() -> dict`; `scrape_tiktok_profile(username: str) -> Optional[Dict]`.

**Data Shape:** client = `httpx.Client(follow_redirects=True, timeout=20, proxy=get_httpx_proxy())`; headers carry the full Sec-Fetch trio (`Sec-Fetch-Mode: navigate`, `Sec-Fetch-Site: none`, `Sec-Fetch-Dest: document`) plus `Sec-Ch-Ua-Mobile: ?0` / `Sec-Ch-Ua-Platform: "Windows"`; profile dict = 10 keys incl. `is_verified`, `likes_count`, `video_count`.

### Decisive source

```python
_client = None

def _get_client():
    global _client
    if _client is None:
        proxy = get_httpx_proxy()
        _client = httpx.Client(follow_redirects=True, timeout=20, proxy=proxy)
    return _client
```

**Flow:** lazy first call reads the proxy ladder ONCE via `get_httpx_proxy()` (the scheme-prefixed accessor — see `proxy-ladder.md`) and freezes it into a process-wide client; every subsequent scrape reuses that connection pool but calls `_build_headers()` PER REQUEST so each request still gets a fresh `random_user_agent()`. The hydration walk itself (fixed-scope `__DEFAULT_SCOPE__['webapp.user-detail']` with KeyError/TypeError → None) is owned by `rehydration-extraction.md`; this capsule owns the fetch layer around it.

**Invariant:** three decisions a porter gets wrong. (1) The proxy snapshot is read at FIRST USE, not import time — env changes after the first request are ignored for tiktok only (requests-based platforms re-read per call); restarting the process is the only way to re-arm tiktok's egress, which is also why the settings menu never hot-swaps proxies mid-session for this platform. (2) Error handling is TYPED and total: `httpx.HTTPStatusError` (from `raise_for_status()`) and `httpx.RequestError` both log-and-return-None, i.e. tiktok speaks the loop's SKIP dialect and can NEVER raise into `_standard_scrape_loop`'s RuntimeError break — a batch of dead usernames degrades item-by-item instead of aborting. If you port this to raise on HTTP failures you silently change batch semantics owned by `scrape-loop-export.md`. (3) The header set is deliberately richer than the other scrapers' minimal trio (UA/Accept/Accept-Language): TikTok's edge serves different content to requests missing Sec-Fetch/Client-Hints headers, so the extra fields are load-bearing anti-bot hygiene, not decoration.

**Probe:** no upstream tests. Deterministic pins: `grep -n "global _client\|follow_redirects=True\|Sec-Fetch" app/scrapers/tiktok.py` → :14/:21/:31-33. Executable (no network):

```
python3 - <<'EOF'
import sys, os; sys.path.insert(0, '<repo>')
os.environ['SCOUT_PROXY'] = '127.0.0.1:9'
import httpx
import app.scrapers.tiktok as tk
captured = {}
real = httpx.Client
httpx.Client = lambda **kw: (captured.update(kw), real(**kw))[1]   # spy ctor kwargs
tk._client = None                      # reset singleton
c = tk._get_client()
assert captured['proxy'] == 'http://127.0.0.1:9'      # scheme prefix applied
assert captured['follow_redirects'] is True and captured['timeout'] == 20
assert tk._get_client() is c                          # singleton reuse
EOF
```

**Retrieve:**

```ts
await mcp.codebase-memory.search_graph({ project: "Scout", query: "_get_client _build_headers tiktok httpx proxy", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the lazy-once client + per-request UA rotation + typed-total error swallow as the httpx twin of the requests-based scrapers; adapt timeouts and header richness to your target; omit nothing — dropping the Sec-Fetch set or switching to per-call clients both measurably change success rates against the real edge.
