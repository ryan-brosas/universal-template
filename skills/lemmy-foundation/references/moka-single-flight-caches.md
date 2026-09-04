<!-- capsule-v2 -->
# Moka single-flight caches — how do you cache DB reads across async tasks without stampedes or stale ids?

**Source:** lemmy AGPL-3.0 `main@439734dd638a2c06a2f907beab7dcf4646e88f86`; Codebase Memory `ext-lemmy`. **Question:** Three different read patterns (immutable actor, immutable activity, hot max-id) share one cache library — what TTL/capacity policy does each get and why?

## util.rs cache trio
**Path/Symbol:** `crates/apub/send/src/util.rs` — `get_actor_cached` (:135–175), `get_activity_cached` (:182–194), `get_latest_activity_id` (:197–215); knobs `CACHE_DURATION_LATEST_ID` (:69–78, 1 s prod / = recheck delay in tests), `WORK_FINISHED_RECHECK_DELAY` (:57–63, 30 s).
**Signature:** all three: `async fn get_*(pool: &mut DbPool<'_>, key) -> Result<T>` wrapping `CACHE.try_get_with(key, load_future)`.
**Data Shape:** statics via `LazyLock`: actors `Cache<Url, Arc<SiteOrMultiOrCommunityOrUser>>` cap 10 000 NO TTL; activities `Cache<ActivityId, Option<Arc<SentActivity>>>` cap 10 000 NO TTL; latest id `Cache<(), Option<ActivityId>>` TTL-only (single-unit key ⇒ process-wide throttle).

### Decisive source
```rust
// util.rs:140-143 — try_get_with = per-key single-flight: concurrent misses for the SAME key
// share ONE db load; other keys proceed independently. Arc value = cheap sharing across workers.
static CACHE: LazyLock<Cache<Url, Arc<SiteOrMultiOrCommunityOrUser>>> =
  LazyLock::new(|| Cache::builder().max_capacity(10000).build());
CACHE.try_get_with(actor_apub_id.clone(), async {
  let actor = match actor_type { Site => ..., Community => ..., Person => ..., MultiCommunity => ... };
  Result::<_, LemmyError>::Ok(Arc::new(actor))
}).await

// util.rs:196-203 — the "latest id" cache uses a () key: every caller shares one entry,
// so the effect is a min-interval throttle on max(id) queries, not a lookup cache
static CACHE: LazyLock<Cache<(), Option<ActivityId>>> =
  LazyLock::new(|| Cache::builder().time_to_live(*CACHE_DURATION_LATEST_ID).build());
```

**Flow:** worker needs an activity → `get_activity_cached` coalesces concurrent loads of that id (workers across instances race on the same hot rows) → actor resolution before signing is cached forever because AP public keys/ids are immutable-by-assumption → the loop's newest-id probe is throttled to ≤1 query/second fleet-wide by the unit-key TTL cache. Negative lookups: a missing activity row is NOT cached as None here (`try_get_with` error propagates; the worker treats Err as skip) — only `get_latest_activity_id` caches the nullable answer deliberately.
**Invariant:** immutability is what licenses no-TTL caching — porters must confirm their entities never mutate before dropping TTLs; the unit-key pattern turns any cache into a rate limiter; capacity bounds replace eviction tuning where entries are small.
**Probe:** no dedicated unit tests for this module at this pin (coverage caveat — exercised indirectly by the full worker test battery `crates/apub/send/src/worker.rs` `test_send_*`, which drive these caches on every send); constants pinned by usage in `worker.rs` loop.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-lemmy", name_pattern: "get_actor_cached", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt try_get_with single-flight coalescing, the immutable-entity no-TTL cache, and the unit-key throttle-cache for hot aggregate probes. Adapt capacities to your memory budget and add TTLs wherever your entities mutate. Omit the moka dependency if your stack has an equivalent single-flight primitive — the CONTRACT is what ports.
