<!-- capsule-v2 -->
# Env-ladder Redis URLs — why does one deployment need three independent Redis addresses, and what is the fallback chain per tier?

**Source:** nocodb (Sustainable Use License) `develop@640fe3b06f`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-nocodb`. **Question:** Which env wins for cache vs jobs vs throttler, and what happens when only NC_REDIS_URL is set?

## Tiered getters over a common fallback
**Path/Symbol:** `packages/nocodb/src/helpers/redisHelpers.ts:getRedisURL` (whole 30L; NC_REDIS_TTL 3d / NC_REDIS_GRACE_TTL 1d constants).
**Signature:** `getRedisURL(type?: NC_REDIS_TYPE): string | undefined` where type ∈ {CACHE, JOB, THROTTLER}.
**Data Shape:** CACHE: `NC_CACHE_REDIS_URL || NC_REDIS_URL`; JOB: `NC_REDIS_JOB_URL || NC_JOBS_REDIS_URL || NC_REDIS_URL` (two legacy spellings); THROTTLER: `NC_RATE_LIMIT_REDIS_URL || NC_THROTTLER_REDIS || NC_REDIS_URL`; default = CACHE ladder.

### Decisive source
```ts
export const getRedisURL = (type?: NC_REDIS_TYPE) => {
  switch (type) {
    case NC_REDIS_TYPE.CACHE:
      return process.env.NC_CACHE_REDIS_URL || process.env.NC_REDIS_URL;
    case NC_REDIS_TYPE.JOB:
      return (
        process.env.NC_REDIS_JOB_URL ||
        process.env.NC_JOBS_REDIS_URL ||
        process.env.NC_REDIS_URL
      );
```
(:11–:20)

**Flow:** every consumer resolves its tier through this ONE function — NocoCache.init (no arg = cache tier), PubSubRedis (JOB), jobs Bull queues (JOB), throttler stores (THROTTLER), RedisIoAdapter (default/cache), telemetry — so operators can split load across instances or collapse to one shared Redis by setting only NC_REDIS_URL.
**Invariant:** availability checks and connections MUST use the same getter+tier or a pod could think Redis is absent while another plane uses it (PubSubRedis.available literally calls getRedisURL(JOB)). Adding a new legacy env spelling goes in the ladder, never at call sites. TTL constants are env-overridable seconds with day-scale defaults.
**Probe:** `cd packages/nocodb && grep -c "NC_REDIS_URL" src/helpers/redisHelpers.ts` (=4 occurrences incl comments/substring) and `grep -c "getRedisURL" src/helpers/redisHelpers.ts` (=1 def).
**Direct test:** none upstream — grep probes pin shape.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-nocodb", query: "getRedisURL NC_REDIS_TYPE CACHE JOB THROTTLER", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the tiered-getter pattern so each infra plane can be isolated or collapsed via env; adapt names to your convention; omit if you run exactly one Redis forever. Coverage caveat: grep-pinned only.
