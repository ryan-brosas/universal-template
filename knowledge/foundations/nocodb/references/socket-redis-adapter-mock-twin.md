<!-- capsule-v2 -->
# Socket.IO Redis adapter with in-memory twin — how does a single-node install get the same websocket code path as a cluster?

**Source:** nocodb (Sustainable Use License) `develop@640fe3b06f`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-nocodb`. **Question:** How do you avoid forking your realtime logic between "one pod" and "many pods" deployments?

## ioredis-mock fallback keeps ONE code path
**Path/Symbol:** `packages/nocodb/src/gateways/RedisIoAdapter.ts:RedisIoAdapter` (whole 32L); wired at `src/Noco.ts:221` (`new RedisIoAdapter(httpServer)` → `connectToRedis()` → `useWebSocketAdapter`).
**Signature:** `connectToRedis(): Promise<void>`; `createIOServer(port: number, options?: ServerOptions): any`.
**Data Shape:** redisUrl from `getRedisURL()` (cache-tier env ladder); pub client + `pubClient.duplicate()` sub client feed `createAdapter`.

### Decisive source
```ts
const redisUrl = getRedisURL();

if (redisUrl) {
  pubClient = new Redis(redisUrl);
} else {
  pubClient = new RedisMock();
}

const subClient = pubClient.duplicate();
this.adapterConstructor = createAdapter(pubClient, subClient);
```
(:14–:24)

**Flow:** at boot (before nestApp.init), build the adapter constructor from real Redis when NC_CACHE_REDIS_URL/NC_REDIS_URL is set, else from an IN-MEMORY ioredis-mock → createIOServer attaches it to every spawned server. Broadcasts emitted through socket.io (`io.emit`, room emits) then behave identically locally and cross-pod; Noco.ts logs 'Websocket adapter initialized'.
**Invariant:** application code must never branch on deployment shape — the mock makes single-node a degenerate cluster. The duplicate() sub client is required by @socket.io/redis-adapter (pub/sub cannot share one connection). Note this is the socket.io fan-out plane only; job/pubsub messaging uses PubSubRedis separately.
**Probe:** `cd packages/nocodb && grep -c "ioredis-mock\|RedisMock" src/gateways/RedisIoAdapter.ts` (=2: import + construction) and `grep -c "duplicate" src/gateways/RedisIoAdapter.ts` (=1).
**Direct test:** none upstream — grep probes pin the contract.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-nocodb", query: "RedisIoAdapter connectToRedis createIOServer", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the mock-backed adapter so one broadcast API serves both topologies; adapt the URL ladder to your env naming; omit if you require Redis unconditionally. Coverage caveat: grep-pinned only.
