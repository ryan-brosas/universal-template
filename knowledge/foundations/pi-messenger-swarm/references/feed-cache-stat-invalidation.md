<!-- capsule-v2 -->
# Feed event cache stat-pair invalidation — how does a hot UI loop re-read an append-only file without re-parsing it every render?

**Source:** pi-messenger-swarm MIT `main@6fe429a4b74ae276a621bb72910d7926fb6b3104`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-pi-messenger-swarm`. **Question:** What is the exact cache key discipline that makes 100ms-TTL feed reads cheap yet never stale?

## mtime+size pair gate over TTL
**Path/Symbol:** `feed/index.ts:loadFeedCache` (:130-183), `FEED_CACHE_TTL_MS = 100` (:68), `appendFeedEvent` → `invalidateFeedCache` (:77-80, :185-204).
**Signature:** `loadFeedCache(cwd, channelId): FeedCacheEntry | null` where entry carries `lines: string[]` AND parsed `events: FeedEvent[]`.
**Data Shape:** `FeedCacheEntry { mtimeMs, size, expiresAt, lines, events }` in a module-level `Map<absPath, entry>`.

### Decisive source
```ts
const cached = feedCache.get(p);
if (cached && cached.expiresAt > now) return cached;          // 100ms TTL fast path
...
const stat = fs.statSync(p);
if (cached && cached.mtimeMs === stat.mtimeMs && cached.size === stat.size) {
  cached.expiresAt = now + FEED_CACHE_TTL_MS;                  // unchanged ⇒ slide TTL only
  return cached;
}
```

**Flow:** TTL hit → return; else stat the channel jsonl — if mtime+size BOTH equal the cached pair, keep parsed lines and merely extend expiry (append-only files change size monotonically, so size equality is a strong no-change signal); otherwise full read+parse once and store both raw lines and sanitized events. Writers call `invalidateFeedCache` immediately after append so the local process never sees its own write late.
**Invariant:** The stat-pair check is what survives the TTL window: after 100ms the cache is NOT discarded, it is validated against mtime+size first. Porters who treat TTL as the only freshness mechanism re-parse constantly; porters who skip the pair-check serve stale feeds forever.
**Probe:** direct test `tests/feed.test.ts::writes events to the unified channel JSONL file` (:25) + `::prunes events within the project-scoped feed` (:56); `grep -c "cached.mtimeMs === stat.mtimeMs && cached.size === stat.size" feed/index.ts` (=1).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-pi-messenger-swarm", query: "loadFeedCache FEED_CACHE_TTL invalidateFeedCache appendFeedEvent", limit: 5 });
```

## Verdict
Adopt stat-pair validation under a short TTL for any append-only log reader; adapt TTL to your render cadence; omit the dual lines/events storage if you never need raw-line access.
