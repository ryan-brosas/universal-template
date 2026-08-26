<!-- capsule-v2 -->
# Notification long-poll registry — how does a pod hold per-user HTTP responses open and wake them from ANY instance without a websocket?

**Source:** nocodb (Sustainable Use License) `develop@640fe3b06fb2`; Codebase Memory `nocodb`. **Question:** How do you deliver cross-instance user notifications to browsers that only have a plain HTTP long-poll, and when is the Redis channel subscribed/unsubscribed?

## Held-response registry + refcounted Redis channel
**Path/Symbol:** `packages/nocodb/src/controllers/notifications.controller.ts:notificationPoll` (:49–88); `packages/nocodb/src/services/notifications/notifications.service.ts` registry (:22–66) and fan-out (:68–78).
**Signature:** `addConnection(userId, res)` / `removeConnection(userId, res, unsubscribeCb: (keepRedisChannel?: boolean) => Promise<void> | null)` / `sendToConnections(key, payload): void`.
**Data Shape:** `connections: Map<string, (Response & { resId: string })[]>`; res stamped `res.resId = nanoidv2()` (14-char custom nanoid); channel `notification:<userId>`; payloads are JSON strings.

### Decisive source
```ts
// controller: hold the response, subscribe once per poll request
res.setHeader('Cache-Control', 'no-cache, must-revalidate');
res.resId = nanoidv2();
this.notificationsService.addConnection(req.user.id, res);
let unsubscribeCallback = null;
if (PubSubRedis.available) {
  unsubscribeCallback = await PubSubRedis.subscribe(
    `notification:${req.user.id}`,
    async (data) => { this.notificationsService.sendToConnections(req.user.id, data); },
  );
}
res.on('close', async () => {
  await this.notificationsService.removeConnection(req.user.id, res, unsubscribeCallback);
});
setTimeout(() => {
  if (!res.headersSent) res.send({ status: 'refresh' });
}, POLL_INTERVAL /* 30000 */).unref();

// service: LAST local connection out drops the channel; earlier ones keep it
if (userConnections.length === 0) {
  this.connections.delete(userId);
  if (unsubscribeCb) await unsubscribeCb();
} else {
  if (unsubscribeCb) await unsubscribeCb(true); // keep redis channel
}

// delivery wakes EVERY held response for the user, then clears wholesale
for (const res of connections ?? []) res.send({ status: 'success', data: payload });
this.removeConnectionByUserId(key);
```
(controller :56–87; service :54–65, :68–78)

**Flow:** poll → register res under userId → subscribe redis channel (once per request; PubSubRedis demuxes/refcounts internally — see refcounted-pubsub-demux) → any instance's insertNotification publishes → every local held res gets `{status:'success',data}` → registry entry cleared wholesale → clients close, re-list, re-poll. Client-visible vocabulary: `success` (payload) vs `refresh` (30s keepalive or shutdown flush — "re-poll now").
**Invariant:** the Redis channel must outlive PARTIAL disconnects (`unsubscribeCb(true)` keeps it while any local connection remains) but may drop on the last one; the 30s timer only answers when headers were never sent and is `.unref()`'d so it never holds process exit; `onModuleDestroy` flushes every still-open response with `{status:'refresh'}` unless headers sent — same ladder as jobs-listen-shutdown-flush. After a successful fan-out the whole map entry is deleted, so late `close` handlers no-op WITHOUT running their unsubscribe callback (the subscription intentionally lingers until pod death; callbacks tolerate empty registries).
**Probe:** `grep -c "POLL_INTERVAL" packages/nocodb/src/controllers/notifications.controller.ts` (=2: decl :26 + use :81) · `grep -c "status: 'refresh'" packages/nocodb/src/controllers/notifications.controller.ts` (=2: keepalive :38-ish window + poll timer :84... both send sites) · `grep -c "keepRedisChannel" packages/nocodb/src/services/notifications/notifications.service.ts` (=1: the PARAMETER decl :40 — the keep-call passes positional `true` at :63) · `grep -c "removeConnectionByUserId" packages/nocodb/src/services/notifications/notifications.service.ts` (=2: decl :80 + fan-out tail :77).
**Direct test:** none upstream beyond "should be defined" shells (notifications.controller.spec.ts / notifications.service.spec.ts) — probes pin shape.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", file_pattern: "*notifications*", limit: 20 });
```

## Verdict
Adopt held-response-per-user registry + pubsub wakeup + refcounted channel teardown for any multi-instance push-to-browser need over plain HTTP; adapt interval, payload envelope keys, and whether fan-out closes all pollers (NocoDB's one-shot wake-all-and-clear) to your client generation; omit Redis tier entirely for single-instance installs (`PubSubRedis.available` gate already degrades cleanly). Coverage caveat: no behavioral upstream tests; graph coverage clean (full mode @pin).
