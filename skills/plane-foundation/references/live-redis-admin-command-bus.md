<!-- capsule-v2 -->
# Redis admin command bus + fleet-wide stateless broadcast — how do instances coordinate and how does an event reach ALL servers holding a document?

**Source:** plane AGPL-3.0-only `preview@e056bbf9eb6b511cdc0a5823b1bd6922e561a485`; Codebase Memory `plane`. **Question:** Hocuspocus's Redis extension already syncs Yjs updates per-document — how does Plane layer a validated admin-command channel on top, and what wire trick makes a broadcast execute on every server instead of one?

## Admin channel & zero-identifier broadcast
**Path/Symbol:** `apps/live/src/extensions/redis.ts:Redis` (:24–141), `src/redis.ts:RedisManager` (:11–217), `src/utils/broadcast-message.ts:broadcastMessageToPage` (:13–44).
**Signature:** `onAdminCommand<T>(command: AdminCommand, handler): void`; `publishAdminCommand<T>(data: T): Promise<number>`; `broadcastToDocument(documentName: string, payload: unknown): Promise<number>`; `broadcastMessageToPage(instance, documentName, eventData): Promise<boolean>`.
**Data Shape:** Class extends `HocuspocusRedis`, constructed with the shared ioredis client from `redisManager.getClient()` (pub/sub duplicates inherit the manager's tuning: keepAlive 30 s, connectTimeout 10 s, maxRetriesPerRequest 3, offline queue on, retry backoff min(t×50, 2000)). Admin envelope `{command, ...}` validated against the `AdminCommand` enum (`force_close`, `health_check`, `restart_document`); handlers live in a private Map.

### Decisive source
```ts
public async broadcastToDocument(documentName: string, payload: unknown): Promise<number> {
  const stringPayload = typeof payload === "string" ? payload : JSON.stringify(payload);
  const message = new OutgoingMessage(documentName).writeBroadcastStateless(stringPayload);
  const emptyPrefix = Buffer.concat([Buffer.from([0])]);          // empty identifier
  const channel = this["pubKey"](documentName);
  const encodedMessage = Buffer.concat([emptyPrefix, Buffer.from(message.toUint8Array())]);
  const result = await this.pub.publishBuffer(channel, encodedMessage);
  return result;
}
// admin side
this.sub.subscribe(this.ADMIN_CHANNEL, ...);                      // "hocuspocus:admin"
this.sub.on("message", this.handleAdminMessage);
// handleAdminMessage: JSON.parse → validate command enum → dispatch Map → else warn
```

**Flow:** construct Redis extension eagerly (throws AppError if the manager has no connected client) → `onConfigure`: super-configures doc channels, then subscribes to `hocuspocus:admin` and attaches ONE bound message listener → inbound admin messages are parsed, enum-validated, dispatched to a registered handler or warned → `onDestroy`: unsubscribe + removeListener before super.onDestroy (listener-leak hygiene). Any server-side emitter calls `broadcastMessageToPage`, which finds the Redis extension via `instance.configuration.extensions.find(ext => ext instanceof Redis)` and delegates; publish returns subscriber count for logging.
**Invariant:** The single zero byte before the encoded OutgoingMessage is the "empty identifier" — hocuspocus routes messages with an identifier to the OWNING server only, while empty-identifier messages are processed by EVERY server. Getting this wrong silently turns fleet-wide events into single-server events. The admin listener must be a stable bound reference so `removeListener` in onDestroy actually removes it.
**Probe:** No dedicated upstream test. Deterministic pins: redis.ts contains `Buffer.from([0])`, `"hocuspocus:admin"`, and `publishBuffer`; redis.ts (manager) contains `enableOfflineQueue: true` and `Math.min(times * 50, 2000)`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "plane", query: "publishAdminCommand admin channel redis broadcast document", limit: 5 });
```
Observed at pin: rank-1..4 = Redis.publishAdminCommand/:91–102, broadcastToDocument/:126–140, handleAdminMessage, onAdminCommand.

## Verdict
Adopt the enum-validated command bus over a dedicated channel, bound-listener unsubscribe hygiene, connection-tuning inheritance through `.duplicate()`, and the zero-identifier-byte all-servers broadcast; adapt channel names and command set; omit Plane's coupling to hocuspocus internals (`this["pubKey"]`) only if your CRDT server offers a public equivalent — otherwise reproduce the framing exactly. Coverage caveat: whole-file reads @ pin; no upstream tests.
