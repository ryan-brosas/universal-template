<!-- capsule-v2 -->
# Webhook registration choreography — how do you add a two-sided resource (doc row + external secret) without leaving either half orphaned?

**Source:** grist-core MIT `main@b83224bbe9c88910dfeb28922df254a26f702f68`; Codebase Memory `grist-core`. **Question:** Registration writes a homeDB secret AND applies an AddRecord into the live document — what is the ordering, compensation, and locking discipline?

## Secret first, then doc record, compensating delete on failure — all under a time-capped doc mutex
**Path/Symbol:** `app/server/lib/DocApiTriggers.ts`: `withDocTriggersLock` (242–254), `registerWebhook` (256–298), fork guard (257–259); lock source `ActiveDoc.triggersLock: Mutex` (`app/server/lib/ActiveDoc.ts:292`); queue invalidation calls `activeDoc.webhookQueue.clearWebhookCache(webhookId)` / `activeDoc.triggers.clearCache()` (removeWebhook 313–332).
**Signature:** `withDocTriggersLock(callback: WithDocHandler)` wrapping `triggersLock.runExclusive(...)` with `timeoutReached(MAX_DOC_TRIGGERS_LOCK_MS=15_000, promise, { rethrow: true })`.
**Data Shape:** success payload `{ unsubscribeKey, triggerId (retValues[0]), webhookId }`; batch POST returns `{ webhooks: [{ id }] }`.

### Decisive source
```ts
if (await timeoutReached(MAX_DOC_TRIGGERS_LOCK_MS, callback(activeDoc, req, resp), { rethrow: true })) {
  log.rawError(`Webhook endpoint timed out, releasing mutex`, {...});
}
// registerWebhook:
const webhookId = (await this._dbManager.addSecret(secretValue, activeDoc.docName)).id;
try {
  const sandboxRes = await handleSandboxError("_grist_Triggers", [],
    activeDoc.applyWebhookActions(docSessionFromRequest(req),
      [["AddRecord", "_grist_Triggers", null, { enabled: true, ...fields,
        actions: JSON.stringify([{ type: "webhook", id: webhookId }]) }]]));
  return { unsubscribeKey, triggerId: sandboxRes.retValues[0], webhookId };
} catch (err) {
  await this._dbManager.removeWebhook(webhookId, activeDoc.docName, "", false); // compensate
  throw err;
} finally {
  await activeDoc.sendWebhookNotification();     // wake the delivery loop even on failure paths
}
```

**Flow:** every mutating webhook/trigger route runs inside the SAME per-active-doc mutex so configuration changes and queue clears cannot interleave ("prevent simultaneous changes ... which could lead to weird problems") — but the mutex is held at most 15s: a stuck call (notably one blocked applying user actions against a full action queue) releases the lock anyway while still finishing in the background, so a queue-clear/disable call can ALWAYS get through. Ordering: fork check → URL allowlist → secret created → doc AddRecord → on ANY failure the secret is deleted again (compensating action; empty unsubscribeKey + skip-check flags because this is an internal rollback) → notification sent regardless.
**Invariant:** the doc may transiently contain an id whose secret was deleted, but the secret table must never accumulate registrations whose doc row was refused — hence compensation runs BEFORE rethrow. Cache invalidation (webhookQueue + triggers caches) accompanies every removal/update so the delivery loop never serves stale config. Read-only monitor endpoints deliberately run WITHOUT the lock.
**Probe:** `test/server/lib/docapi/DocApiTriggers.ts` full CRUD ladder :48–212 (:82 reject-without-tableRef, :179/:191 delete paths); mutex behavior pinned indirectly via `test/server/lib/Webhooks-Proxy.ts`; direct unit test of the 15s cap absent — caveat.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core",
  query: "applyWebhookActions sendWebhookNotification clearWebhookQueue triggersLock", limit: 10,
  fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the pattern for any resource spanning a durable store and a replicated/live surface: create external half first, live half second, compensate the external half on failure, notify consumers in finally. Adopt the capped mutex whenever a lock holder can block on the very queue another route needs to drain. Adapt the 15s constant to your worst-case action latency; omit checkpoint/restart interplay.
