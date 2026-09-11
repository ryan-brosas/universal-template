<!-- capsule-v2 -->
# Notification triple delivery — where does an in-app notification get written, and which planes carry it to the user?

**Source:** nocodb (Sustainable Use License) `develop@640fe3b06fb2`; Codebase Memory `nocodb`. **Question:** One user event must reach a durable inbox AND a browser that may be connected to a different pod — what are the exact write/delivery steps and who produces these events?

## Durable row + pubsub publish + local fan-out, fed by the app-events bus
**Path/Symbol:** `packages/nocodb/src/services/notifications/notifications.service.ts:insertNotification` (:84–101) and `hookHandler`/:onModuleInit (:187–259); model `packages/nocodb/src/models/Notification.ts` (:21–39 insert, :58–94 list).
**Signature:** `insertNotification(insertData: Partial<Notification>, _req)`; producers call `appHooks.on(AppEvents.PROJECT_INVITE | AppEvents.WELCOME, handler)`.
**Data Shape:** row {id, body (JSON string via prepareForDb), type: AppEvents, fk_user_id, is_read, is_deleted}; publish/local payload = `JSON.stringify(insertData, getCircularReplacer())`.

### Decisive source
```ts
protected async insertNotification(insertData, _req) {
  await Notification.insert(insertData);                    // 1. durable inbox row
  if (PubSubRedis.available) {
    await PubSubRedis.publish(                              // 2. cross-pod wakeup
      `notification:${insertData.fk_user_id}`, JSON.stringify(insertData, getCircularReplacer()));
  }
  this.sendToConnections(                                   // 3. same-pod immediate fan-out
    insertData.fk_user_id, JSON.stringify(insertData, getCircularReplacer()));
}
```
(:84–101)

**Flow:** services emit typed AppEvents (PROJECT_INVITE emitters: `src/services/base-users/base-users.service.ts:260` and :302 after base invites) → NotificationsService.hookHandler (registered in onModuleInit, unsubs collected for onModuleDestroy) shapes a minimal body ({base:{id,title,type}, user:{id,email,displayName,meta}} for invites; {} for WELCOME) → triple delivery above → list endpoint returns PagedResponseImpl carrying a THIRD-ARG envelope `{ unreadCount }` beside pageInfo (list + count + unread count = three queries).
**Invariant:** the durable row is written even when Redis is absent (publish is gated, insert is NOT); body JSON round-trips through prepareForDb('body') on write and prepareForResponse('body') on read (see meta-json-column-codec); ownership checks resolve by BOTH id and fk_user_id before update/delete (`Notification.get({id, fk_user_id})` else NcError.unauthorized); delete is SOFT (is_deleted:true) and list always filters `is_deleted:false`; PATCH bodies are narrowed server-side to ['is_read']. Note the asymmetry this plane lives in: notifications ride the app-events bus while MailService.sendMail is invoked INLINE by services — two coexisting delivery idioms.
**Probe:** `grep -c "AppEvents.PROJECT_INVITE" packages/nocodb/src/services/base-users/base-users.service.ts` (=2 emits :260,:302) · `grep -c "unreadCount" packages/nocodb/src/services/notifications/notifications.service.ts` (=2: var + envelope) · `grep -c "getCircularReplacer" packages/nocodb/src/services/notifications/notifications.service.ts` (=3: import + 2 serializations) · `grep -cE "prepareForDb|prepareForResponse" packages/nocodb/src/models/Notification.ts` (=4 lines: import + insert + list + update).
**Direct test:** none upstream beyond instantiation shells — probes pin shape.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "insertNotification hookHandler PROJECT_INVITE WELCOME notification", limit: 10 });
```

## Verdict
Adopt the triple-delivery ordering (persist first, then two lossy channels) and event-bus-driven production so producers stay decoupled from notification shaping; adapt the body schema per event type and the unread-count envelope to your API shape; omit the pubsub leg for single-process hosts (the gate is already in the right place). Coverage caveat: grep-pinned only, no behavioral upstream tests.
