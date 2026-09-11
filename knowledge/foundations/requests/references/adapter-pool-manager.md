<!-- capsule-v2 -->
# Pool manager construction — how are pool sizes, retries, and proxy managers initialized and cached per adapter?

**Source:** psf/requests Apache-2.0 `main@8f8b212de8c2129d7954c6cd373762880375620a`; Codebase Memory `ext-requests`. **Question:** What do DEFAULT_POOLSIZE/DEFAULT_RETRIES mean at construction, and how does `proxy_manager_for` cache managers?

## HTTPAdapter.__init__ / init_poolmanager / proxy_manager_for / __setstate__
**Path/Symbol:** `src/requests/adapters.py:HTTPAdapter.__init__` (:201-221), `.init_poolmanager` (:239-267), `.proxy_manager_for` (:269-305), `.__setstate__` (:226-237).
**Signature:** `__init__(pool_connections=10, pool_maxsize=10, max_retries=0|Retry, pool_block=False)`; `proxy_manager_for(proxy: str, **proxy_kwargs)`.
**Data Shape:** Module constants :79-82: `DEFAULT_POOLBLOCK=False, DEFAULT_POOLSIZE=10, DEFAULT_RETRIES=0, DEFAULT_POOL_TIMEOUT=None`.

### Decisive source
```python
if max_retries == DEFAULT_RETRIES:
    self.max_retries = Retry(0, read=False)     # connect-only retries; reads NEVER retried by default
else:
    self.max_retries = Retry.from_int(max_retries)
...
def init_poolmanager(self, connections, maxsize, block=DEFAULT_POOLBLOCK, **pool_kwargs):
    # save these values for pickling
    self._pool_connections = connections
    self._pool_maxsize = maxsize
    self._pool_block = block
    self.poolmanager = PoolManager(num_pools=connections, maxsize=maxsize,
                                   block=block, **pool_kwargs)
...
# proxy_manager_for: one manager PER PROXY URL, cached in self.proxy_manager dict
if proxy in self.proxy_manager:
    manager = self.proxy_manager[proxy]
elif proxy.lower().startswith("socks"):
    username, password = get_auth_from_url(proxy)
    manager = self.proxy_manager[proxy] = SOCKSProxyManager(proxy, ...)
else:
    manager = self.proxy_manager[proxy] = proxy_from_url(
        proxy, proxy_headers=self.proxy_headers(proxy), ...)
```

**Flow:** constructor stores pool params as `_pool_*` privates BEFORE building the PoolManager (they're the pickle contract in `__attrs__`) → default max_retries is `Retry(0, read=False)`: zero total but read=False means body-reads are never retried — passing an int uses `Retry.from_int` semantics instead → unpickling rebuilds poolmanager from the three saved scalars and resets `proxy_manager={}` (the lambda-backed poolmanager isn't pickleable) → proxy managers cached keyed by exact proxy URL string; SOCKS branch extracts embedded auth and requires optional dependency else `InvalidSchema("Missing dependencies for SOCKS support.")`.
**Invariant:** The docstring constraint porters must keep: max_retries applies ONLY to failed DNS/socket-connect/connect-timeouts — "never to requests where data has made it to the server" (read=False). `close()` clears poolmanager AND every cached proxy manager. Per-proxy caching means mutating TLS options after first use of a proxy silently doesn't apply.
**Probe:** Direct tests: `tests/test_requests.py::test_urllib3_retries` (:2740, Retry(total=2, status_forcelist) → RetryError — the read=False default contrast), `::test_urllib3_pool_connection_closed` (:2750, ClosedPoolError→ConnectionError arm); `grep -c "self.proxy_manager\[proxy\]" src/requests/adapters.py` → 3.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-requests", query: "init_poolmanager PoolManager proxy_manager_for", limit: 10 });
```

## Verdict
Adopt Retry(0, read=False) default and pickle-rebuild choreography. Adapt to host pool library keeping the save-scalars-then-build order. Omit SOCKS arm when target env never proxies via SOCKS (keep the loud InvalidSchema fallback anyway).
