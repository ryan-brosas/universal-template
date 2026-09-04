<!-- capsule-v2 -->
# Distributed named lock with swappable backend — how does a library take cross-process locks without hardwiring Redis or files?

**Source:** crewAI MIT `main@9e9a8577becc322f98a966ad88d7904251049744`; Codebase Memory `ext-crewAI`. **Question:** What is the minimal seam that lets an application inject its own locking strategy at startup while the library keeps working standalone?

## Snapshot-the-global backend selection
**Path/Symbol:** `lib/crewai-core/src/crewai_core/lock_store.py` (`set_lock_backend` :45–54, `_redis_available` :57–66, `lock` :80–121; `_DEFAULT_TIMEOUT=120` :35).
**Signature:** `lock(name: str, *, timeout: float = 120) -> Iterator[None]` (contextmanager); `set_lock_backend(backend: LockBackend | None) -> None`.
**Data Shape:** channel = `"crewai:" + md5(name).hexdigest()` — human names are namespaced AND fixed-width; lock file lives in `tempfile.gettempdir()/channel.lock`.

### Decisive source
```python
# Snapshot the global once: a concurrent set_lock_backend() must not turn
# the check-then-call into calling ``None``.
backend = _backend
if backend is not None:
    with backend(name, timeout=timeout):
        yield
    return

channel = f"crewai:{md5(name.encode(), usedforsecurity=False).hexdigest()}"

if _redis_available():
    with portalocker.RedisLock(channel=channel, connection=_redis_connection(), timeout=timeout):
        yield
else:
    ...
    pl = portalocker.Lock(lock_path, timeout=timeout)
    pl.acquire()
```

**Flow:** acquire local snapshot of the backend global → custom backend receives the RAW name verbatim → default path hashes the name into a collision-safe channel and picks Redis (when REDIS_URL set AND redis importable) or portalocker file lock → timeout converts to `LockException` naming name/path/timeout with a multi-process hint → release in finally.
**Invariant:** The one-time-snapshot rule prevents a torn read where `_backend` becomes None between check and call. Hashing means callers may pass arbitrary names (db paths, uuids) without filesystem/Redis key constraints; `usedforsecurity=False` keeps md5 FIPS-legal. In-flight holders keep THEIR backend across swaps. Consumers namespace on top: SQLite flow persistence uses `"sqlite:" + realpath(db_path)` so symlinked paths still contend correctly.
**Probe:** `.venv/bin/python -m pytest lib/crewai/tests/utilities/test_lock_store.py -q` (expect 4 passed incl. file-lock fallback); static anchors: `grep -c "REDIS_URL" lib/crewai-core/src/crewai_core/lock_store.py` → 7, `md5(name.encode` ×1 :97.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-crewAI", query: "lock_store RedisLock portalocker set_lock_backend named lock", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt hash-namespaced channels + snapshot-on-entry backend dispatch + graceful env-based degradation; adapt timeouts per call site; omit the Redis arm for single-host products. Direct tests executed green at pin.
