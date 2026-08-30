<!-- capsule-v2 -->
# Webhook statistics store — where do delivery statuses live when the primary process can restart?

**Source:** grist-core MIT `main@b83224bbe9c88910dfeb28922df254a26f702f68`; Codebase Memory `grist-core`. **Question:** How do you expose per-webhook status/usage to an owner UI when events are transient and redis is optional?

## Hash-of-string-fields with TTL, in-memory fallback, and derived usage view
**Path/Symbol:** `app/server/lib/WebhookQueue.ts:PersistedStore` (646–697), `WebhookStatistics.getUsage/logStatus/logBatch/logInvalid` (703–836), `StatsKey` union (838–849); consumed by `summary()`/`getPendingItems()` (187–327).
**Signature:** `logStatus(id: string, status: WebhookStatus, now?: number | null)`; `logBatch(id, status: WebhookBatchStatus, stats?: { httpStatus?, error?, size?, attempts? })`; `getUsage(id, queue): Promise<WebhookUsage | null>`.
**Data Shape:** one redis hash ``webhooks:${docId}:statistics``; fields ``${webhookId}:${StatsKey}`` all STRINGS (numbers serialized via toString/parseInt round-trip); keys: batchStatus, httpStatus, errorMessage, attempts, size, updatedTime, lastFailureTime, lastSuccessTime, lastErrorMessage, lastHttpStatus, status. In-memory fallback = `MapWithTTL<string,string>` at 24h.

### Decisive source
```ts
protected async set(id: string, keyValues: [Keys, string][]) {
  if (this._redisClient) {
    const multi = this._redisClient.multi();
    for (const [key, value] of keyValues) {
      multi.hset(this._redisKey, `${id}:${key}`, value);
      multi.expire(this._redisKey, WEBHOOK_STATS_CACHE_TTL);   // re-TTL the WHOLE doc hash on every write
    }
    await multi.execAsync();
  } else { /* MapWithTTL fallback */ }
}
public async logStatus(id, status, now?) {
  const stats: [StatsKey, string][] = [["status", status], ["updatedTime", (now ?? Date.now()).toString()]];
  if (status === "sending") { stats.push(["errorMessage", ""]); }   // clear stale error on new attempt
  ...
}
```

**Flow:** every delivery transition writes through `logStatus` (sending/retrying/idle/postponed/error/invalid) or `logBatch` (success/failure/rejected + last-attempt details), each write bumping the 24h expiry so quiet docs age out entirely; `getUsage` reads all fields for a webhook, returns a fully-typed view — empty-everything ⇒ `{status:"idle", numWaiting}` computed from the LIVE in-memory queue length passed in by the caller; batch history surfaces as `lastEventBatch`. Every mutation also fires `markChange()` → pushes a websocket notification so open UIs refresh.
**Invariant:** everything is a string in storage — nulls are "" / absent and re-hydrated via parseInt guards, never stored as JSON nulls; the hash is per-DOCUMENT (one key, field-prefixed per webhook) so cleanup (`clear()`) and expiry are single-key operations; stats are best-effort diagnostics — loss on redis outage degrades the monitoring UI only, never delivery correctness; timestamps accept an injected `now` so near-simultaneous updates coalesce identically.
**Probe:** covered within `test/server/lib/docapi/DocApiWebhooks.ts` mainWebhooks suite (status transitions surfaced via `/webhooks` summary endpoints) — no standalone PersistedStore unit file (coverage caveat noted).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core",
  query: "WebhookStatistics PersistedStore logBatch getUsage", limit: 10,
  fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the shape (per-entity field-prefix hash + whole-key rolling TTL + string-only fields + derived read model) for job/delivery dashboards backed by redis-or-nothing deployments. Adapt TTLs, field names, and the notification hook to host. Omit the fallback Map if your process is single-instance-per-doc like grist's doc workers — but keep the string discipline; it's what makes redis hashes lossless here.
