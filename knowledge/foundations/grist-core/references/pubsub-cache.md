<!-- capsule-v2 -->
# PubSubCache — how does a multi-server TTL cache invalidate cross-process without races?

**Source:** grist-core MIT `main@b83224bbe9c88910dfeb28922df254a26f702f68`; Codebase Memory `grist-core`. **Question:** How do you keep a per-process cache coherent across servers using pub-sub, avoiding both missed invalidations and self-invalidation loops?

## Subscribe-before-fetch + self-id echo suppression
**Path/Symbol:** `app/server/lib/PubSubCache.ts:PubSubCache` (whole file, 86L); built on `mapGetOrSet` + `MapWithCustomExpire` (`app/common/AsyncCreate.ts`); transport via `IPubSubManager` (`app/server/lib/PubSubManager.ts`).
**Signature:** `getValue(key: Key): Promise<Value>`; `invalidateKeys(keys: Key[]): Promise<void>`.
**Data Shape:** `_cache: MapWithCustomExpire<Key, Promise<Value>>` (TTL per option); `_watchedKeys: Map<Key, UnsubscribeCallbackPromise>`; `_selfId` random instance id; invariant comment: "if _cache[key] is set, then _watchedKeys[key] is set."

### Decisive source
```ts
public getValue(key: Key): Promise<Value> {
  return mapGetOrSet(this._cache, key, async () => {
    // Find key in _watchedKeys, or create a new subscription to invalidations.
    await mapGetOrSet(this._watchedKeys, key, () => this._subscribe(key));
    return this._options.fetch(key);     // subscribe BEFORE fetch — no gap for missed msgs
  });
}
public async invalidateKeys(keys: Key[]) {
  for (const key of keys) { this._cache.delete(key); }        // local eviction is synchronous
  await this._options.pubSubManager.publishBatch(
    keys.map(key => ({ channel: this._options.getChannel(key), message: this._selfId })));
}
// on message: ignore our own echo, else evict
msg => (msg === this._selfId ? null : this._cache.delete(key)),
```

**Flow:** get ⇒ cache hit returns → miss ⇒ single-flight (`mapGetOrSet`) ensures one subscription + one fetch per key regardless of concurrent callers → subscription established and CONFIRMED before `fetch` runs, so any invalidation published after the read began is guaranteed to be seen → value cached with TTL. Invalidate ⇒ delete locally first (synchronous), then publish only the instance id as the message body; every other instance's listener deletes the key. When a cache entry expires by TTL, the pub-sub subscription is torn down too (memory bounded), to be re-established on next use.
**Invariant:** the message carries the PUBLISHER'S id, not the key (the channel already names the key) so receivers can distinguish foreign invalidations from their own echo — deleting twice would be harmless but the check documents intent; subscription must exist before fetch completes or an interleaved write could be cached stale forever; failure-clearing from `mapGetOrSet` means a failed fetch retries on next call rather than caching a rejected promise.
**Probe:** `test/server/lib/PubSubCache.ts` — dedicated suite covering cross-instance invalidation, self-echo suppression, and expiry-unsubscribe behavior (run with two in-process instances over the memory pub-sub manager).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core",
  query: "PubSubCache getValue invalidateKeys", limit: 10,
  fields: ["signature", "name", "file"] });
```

## Verdict
Adopt for any N-process cache over shared state (doc metadata, config, entitlements): the subscribe-before-fetch ordering plus id-echo suppression is the whole trick — ~90 lines, transport-agnostic. Adapt channel naming and batch publishing to your bus (redis pub/sub, NATS, postgres LISTEN/NOTIFY). Omit TTL-unsubscribe coupling if you prefer permanent subscriptions at constant memory cost.
