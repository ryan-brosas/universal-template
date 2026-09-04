<!-- capsule-v2 -->
# Redis reply refcount + reconnect ladder — how does a pub/sub request/response client survive disconnects without hanging waiters?

**Source:** nest (MIT) `master@4c38a5ab100f`; Codebase Memory `nest`. **Question:** How do you share one reply subscription across N concurrent requests, clean up at zero, fail-close every pending waiter on loss, and reconnect deterministically?

## Refcounted subscriptions, id-routed replies, three-stage reconnection
**Path/Symbol:** `packages/microservices/client/client-redis.ts:ClientRedis` — `publish` (287-326), `createResponseCallback` (245-285), `handleClose` (187-196), `unsubscribeFromChannel` (339-346), `registerReconnectListener` / `registerReadyListener` / `registerEndListener` / `createRetryStrategy` (116-243), `close` (56-64).
**Signature:** `getRequestPattern(pattern): string` (identity); `getReplyPattern(pattern): string` appends `.reply` to the normalized route; `publish(partialPacket, callback): () => void`.
**Data Shape:** `subscriptionsCount: Map<channel, number>`; `routingMap: Map<id, callback>`; latches `isManuallyClosed`, `wasInitialConnectionSuccessful`, `connectionPromise`.

### Decisive source
```ts
// publish: subscribe-once, count-up per request
if (subscriptionsCount <= 0) {
  this.subClient.subscribe(responseChannel, (err) => !err && publishPacket());
} else {
  publishPacket();
}
// publishPacket(): count++, routingMap.set(packet.id, callback),
//                  pub.publish(getRequestPattern(route), JSON.stringify(serialized))
return () => {                       // teardown per subscriber
  this.unsubscribeFromChannel(responseChannel);   // decrement; unsubscribes at <= 0
  this.routingMap.delete(packet.id);
};
// fail-close on loss:
if (this.routingMap.size > 0) {
  const err = new Error('Connection closed');
  for (const callback of this.routingMap.values()) callback({ err });
  this.routingMap.clear();
}
// reply matching: unknown id ignored, terminal single-callback
const callback = this.routingMap.get(id);
if (!callback) return;
if (isDisposed || err) return callback({ err, response, isDisposed: true });
callback({ err, response });
```

**Flow:** first request subscribes the reply channel then publishes after ack; later requests reuse the channel via counter. Replies JSON-parse with raw-buffer fallback, deserialize to `{err,response,isDisposed,id}`, and dispatch by id; unknown ids (late/duplicate deliveries) are debug-logged and dropped. Connection loss flushes ALL pending callbacks with `Error('Connection closed')` and clears state — no waiter survives a drop. Ladder: RECONNECTING ⇒ park a pre-caught rejected `connectionPromise` + emit status; READY ⇒ resolve promise, emit CONNECTED, attach the message listener exactly once (latched by `wasInitialConnectionSuccessful`); 'end' ⇒ without `retryAttempts`, null both clients for recreate-on-next-connect, else park rejected promise; `retryStrategy` returns undefined (stop) on manual close, missing attempts, or exhausted attempts, else `retryDelay` (default 5000ms).
**Invariant:** manual `close()` sets `isManuallyClosed` BEFORE quit so end-during-close takes the silent manual path (spec asserts the ordering inside the quit callback); every pending correlation either resolves by id or fails closed.
**Probe:** `packages/microservices/test/client/client-redis.spec.ts` (subscribe to the `.reply` channel; sync-publish error calls callback({err}); disposed reply unsubscribes channel + clears routingMap; wrong-id no-call; close() flushes pending with 'Connection closed'; end-during-close ordering assertion).
**Runner caveat:** direct test execution blocked (deps uninstalled); expectations quoted from spec source.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nest", query: "createResponseCallback subscriptionsCount retryStrategy reconnect", file_pattern: "packages/microservices/client/client-redis.ts", limit: 8 });
// live @ pin: rank#1 ClientRedis.createResponseCallback 245-285, rank#2 registerReconnectListener 116-137
```

## Verdict
Adopt refcounted reply channels, id-keyed routing with unknown-id drop, fail-close flushing, and the latch-ordered manual-close suppression; adapt channel naming (the `.reply` suffix) and ioredis event names to your broker client; omit buffer-mode branches unless porting binary transports.
