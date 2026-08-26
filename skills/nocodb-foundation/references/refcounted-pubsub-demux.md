<!-- capsule-v2 -->
# Ref-counted pubsub demux — how do you fan one Redis connection out to N local handlers without MaxListenersExceeded or orphaned channels?

**Source:** nocodb (Sustainable Use License) `develop@640fe3b06f`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-nocodb`. **Question:** When several modules subscribe to the same channel, when is the underlying Redis UNSUBSCRIBE actually safe to send?

## Channel → handler-set map + last-leaver unsubscribe
**Path/Symbol:** `packages/nocodb/src/redis/pubsub-redis.ts:PubSubRedis` (whole 128L); consumers: `src/modules/jobs/redis/jobs-redis.ts` (`JobsRedis.subscribe = PubSubRedis.subscribe`, WORKER/PRIMARY instance channels), notifications.service, use-worker.decorator, jobs-event.service.
**Signature:** `static async init(): Promise<void>`; `static publish(channel, message: string | Record<string,any>): Promise<void>`; `static async subscribe<T>(channel, callback: (message: T, unsubscribe?: (keepRedisChannel?: boolean) => Promise<void>) => Promise<void>): Promise<(keepRedisChannel?: boolean) => Promise<void>>`.
**Data Shape:** `handlers: Map<channel, Set<wrappedFn>>`; messages JSON-parsed best-effort (parse failure delivers raw string).

### Decisive source
```ts
// channel -> handler set. One shared 'message' listener (ensureMessageListener)
// demuxes by channel, instead of one listener per subscribe() (O(N) dispatch +
// MaxListenersExceededWarning past ~10 channels).
async function unsubscribe(keepRedisChannel = false) {
  const set = PubSubRedis.handlers.get(channel);
  if (!set) return;
  set.delete(wrapped);
  if (set.size === 0) {
    PubSubRedis.handlers.delete(channel);
    if (!keepRedisChannel) {
      await PubSubRedis.redisSubscriber.unsubscribe(channel);
    }
  }
}
```
(:16–:18 comment; :105–:116)

**Flow:** lazy init — available is computed once from getRedisURL(JOB); init() opens pub + sub connections on first use; publish() auto-inits and JSON-stringifies objects, swallowing transport errors to log → subscribe() binds ONE shared 'message' listener (idempotent via messageListenerBound flag), registers the wrapped callback in a per-channel Set, and only calls redisSubscriber.subscribe for the FIRST local handler of that channel → delivery demuxes by channel, each handler isolated in its own try/catch (a throw logs and does not starve siblings) → unsubscribe removes the wrapper; the Redis channel closes only when the LAST local handler leaves AND keepRedisChannel is false.
**Invariant:** ref-counting must gate the wire-level UNSUBSCRIBE — dropping it early kills co-subscribers' deliveries. The returned unsubscribe closure accepts keepRedisChannel=true so a subscriber that will re-subscribe (worker restart cycles) can leave the subscription warm. Handler exceptions MUST be caught per-handler or one bad consumer freezes the set's iteration. Static-class state survives hot reload only because consumers hold references; the class is deliberately stateless-per-call otherwise.
**Probe:** `cd packages/nocodb && grep -c "handlers.delete(channel)" src/redis/pubsub-redis.ts` (=1) and `grep -c "ensureMessageListener" src/redis/pubsub-redis.ts` (=3: def + guard + call) and `grep -c "keepRedisChannel" src/redis/pubsub-redis.ts` (=5: type×2 + param + comment + check).
**Direct test:** none upstream — grep probes pin shape.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-nocodb", query: "PubSubRedis ensureMessageListener unsubscribe", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the single-listener demux + refcounted unsubscribe + per-handler error isolation; adapt channel naming to your topology roles; omit if your framework already multiplexes subscriptions. Coverage caveat: grep-pinned only.
