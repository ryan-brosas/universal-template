<!-- capsule-v2 -->
# KeyedMutex + AsyncCreate family — how do you serialize per-key async sections and cache promise-creating work?

**Source:** grist-core MIT `main@b83224bbe9c88910dfeb28922df254a26f702f68`; Codebase Memory `grist-core`. **Question:** What is the minimal correct machinery for per-key mutual exclusion and for "create once, share the pending promise, retry on failure" caching — and what do porters get wrong?

## Map-of-mutexes with GC-on-unlock; promise-caching with clear-on-reject
**Path/Symbol:** `app/common/KeyedMutex.ts:KeyedMutex` (whole file, 46L); `app/common/AsyncCreate.ts` (whole file, 183L): `AsyncCreate.get/_clearOnError` (23–47), `asyncOnce` (54–61), `mapGetOrSet/mapSetOrClear` (72–84), `MapWithTTL.set/delete/clear` (104–149), `freezeError` (172–179).
**Signature:** `acquire(key): Promise<MutexInterface.Releaser>`; `runExclusive<T>(key, cb): Promise<T>`; `mapGetOrSet<K,V>(map: Map<K, Promise<V>>, key, creator): Promise<V>`.
**Data Shape:** `_mutexes: Map<string, Mutex>` (async-mutex instances); `AsyncCreate._value?: Promise<T>` — caches the PROMISE not the value; `MapWithTTL` keeps a parallel `Map<K, Timeout>`.

### Decisive source
```ts
public async acquire(key: string): Promise<MutexInterface.Releaser> {
  if (!this._mutexes.has(key)) { this._mutexes.set(key, new Mutex()); }
  const mutex = this._mutexes.get(key)!;
  const unlock = await mutex.acquire();
  return () => {
    unlock();
    // unlock() leaves the mutex locked if anyone has been waiting for it.
    if (!mutex.isLocked()) { this._mutexes.delete(key); }   // GC only when truly idle
  };
}
// ---- AsyncCreate: share in-flight creation, forget failures
public get(): Promise<T> {
  return this._value || (this._value = this._clearOnError(this._createFunc.call(null)));
}
private _clearOnError(p: Promise<T>): Promise<T> {
  p.catch(() => this.clear());      // rejected create ⇒ next get() tries again
  return p;
}
```

**Flow:** first acquirer creates the mutex and wins; waiters queue inside that same Mutex instance; each releaser deletes the map entry only when nobody is left waiting, so a busy key never loses its queue and an idle key never leaks memory. The AsyncCreate family caches promises so N concurrent `get()` calls run the constructor ONCE and settle together; rejection clears the slot so the NEXT call retries instead of caching poison forever. `mapGetOrSet` applies the same rule per map key; `MapWithTTL` layers lazy expiry via per-key timeouts reset on every `set`, and `MapWithCustomExpire` adds an expiry hook (used to unsubscribe pub-sub listeners); `freezeError` pre-materializes either outcome into `{unfreeze()}` so a cached failure can be replayed on demand.
**Invariant:** the releaser returned by `acquire` must be called exactly once and is NOT safe to call twice — after deletion-and-recreation a stale releaser would unlock a stranger's section; failure-clearing means callers can never observe a cached rejection from AsyncCreate/mapGetOrSet (contrast with memoize libs), but they MUST handle their own retry storms; TTL precision is "may vary" — expiry timers are Node timeouts, cleared on delete/set.
**Probe:** `test/common/KeyedMutex.ts::"orders actions correctly"` (:7) and `::"runs operations exclusively"` (:45) pin serialization semantics; `test/common/AsyncCreate.ts` covers get/clear/retry-on-failure behavior of the family.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core",
  query: "KeyedMutex runExclusive mapGetOrSet MapWithTTL", limit: 10,
  fields: ["signature", "name", "file"] });
```

## Verdict
Adopt all four pieces as the standard concurrency/cache micro-layer: KeyedMutex for per-entity critical sections (grist uses it to serialize snapshot-inventory edits per doc), asyncOnce/mapGetOrSet for single-flight initialization, MapWithTTL(+CustomExpire) for secret/url caches, freezeError where negative caching with manual thaw is needed. Adapt nothing structural — it's ~230 lines total and dependency-free apart from `async-mutex`. Omit KeyedMutex's size getter only if unused; keep the GC-on-unlock invariant even when simplifying.
