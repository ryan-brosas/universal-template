<!-- capsule-v2 -->
# Runtime cache mixins — how does the hash cache behave across threaded/process/uWSGI deployments?

**Source:** isso MIT `master@5ad388d9f10cc5227f6e5d901c249ca888f5ef72`; Codebase Memory `ext-isso`. **Question:** Which cache backend is chosen per deployment and what are the expiry/prune semantics?

## NullCache / SimpleCache / uWSGICache
**Path/Symbol:** `isso/utils/cache.py:SimpleCache` (64–132, vendored cachelib); `isso/core.py:Cache/ThreadedMixin/uWSGIMixin` (21–120).
**Signature:** `Cache(backend)` exposes `get(cache, key) / set(cache, key, value) / delete(cache, key)` — the namespace first-arg is DROPPED on all backends.
**Data Shape:** SimpleCache: threshold=1024 entries, default_timeout=3600s; values pickled `(expires, blob)`.

### Decisive source
```python
# core.py
class Mixin(object):
    def __init__(self, conf):
        self.lock = threading.Lock()
        self.cache = Cache(NullCache())

class ThreadedMixin(Mixin):
    def __init__(self, conf):
        super().__init__(conf)
        if conf.getboolean("moderation", "enabled"):
            self.purge(conf.getint("moderation", "purge-after"))
        self.cache = Cache(SimpleCache(threshold=1024, default_timeout=3600))

# utils/cache.py
def _normalize_timeout(self, timeout):
    timeout = BaseCache._normalize_timeout(self, timeout)
    if timeout > 0:
        timeout = int(time()) + timeout   # 0 => never expires
    return timeout

def get(self, key):
    try:
        expires, value = self._cache[key]
        if expires == 0 or expires > time():
            return self.serializer.loads(value)
    except KeyError:
        return None
```

**Flow:** base `Mixin` installs NullCache (tests/vote suite use `core.Mixin` directly); ThreadedMixin upgrades to in-process SimpleCache; uWSGIMixin swaps to `uwsgi.cache_*` with a fixed 3600s TTL and `cache2` INI config. Pruning happens only inside `set`: expire-scan then oldest-first eviction while over threshold.
**ProcessMixin row (added pass 2, source `isso/core.py:76-79`):** `class ProcessMixin(ThreadedMixin)` — it inherits the SimpleCache upgrade and swaps ONLY the lock (`self.lock = multiprocessing.Lock()`), so under the WSGI-module shim `isso/run.py` (`application = make_app(..., multiprocessing=True)`) each worker process keeps its OWN hash memo cache while sharing SQLite and a cross-process lock. Harmless for memoization, a real trap if you ever store request-scoped state in the cache.
**Invariant:** The two-arg namespace API is compatibility veneer — keys are GLOBAL across namespaces on every backend (isso only uses `"hash"`, so no collision). Expired reads return None silently (no delete-on-read). SimpleCache is explicitly not fully thread-safe (documented).
**Probe:** `grep -c 'threshold or 500' isso/utils/cache.py` (`1`); `grep -c 'expires == 0 or expires > time()' isso/utils/cache.py` (`1`).
**Test:** exercised via test_hash/testVisibleFields through the app; vendored module itself untested upstream (coverage caveat).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-isso", query: "SimpleCache threshold prune expires NullCache", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt backend-swappable cache behind one namespace-tolerant facade. Adapt thresholds/TTLs. Omit cross-namespace key safety unless you actually need multiple namespaces.
