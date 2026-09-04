<!-- capsule-v2 -->
# Reschedule event ladder + bootstrap tombstone guard — how do schedule/unschedule/reschedule map to adapter calls?

**Source:** Ghost MIT `main@81292b004cf59591f03d7dbe01f28f31c09ee813`; Codebase Memory `ext-ghost`. **Question:** Why is reschedule implemented as unschedule+schedule, and why does boot-time rescheduleAll skip the tombstone write?

## PostScheduling event wiring
**Path/Symbol:** `ghost/core/core/server/services/post-scheduling/post-scheduling.ts:PostScheduling` (:28–170; constructor wiring :38–99; `rescheduleAll` :108–129; `#normalize` :144–169).
**Signature:** `constructor({ apiUrl, adapter, internalKeys })`; `rescheduleAll({ previousKey? }): Promise<void>`.
**Data Shape:** SchedulerJob = `{time: published_at unix ms, url: <apiUrl>/schedules/<resource>s/<id>/?token=<jwt>, extra: {httpMethod: 'PUT', oldTime}}`.
### Decisive source
```ts
// Reschedule = matched unschedule + fresh schedule, because tokens
// are signed against the published_at timestamp.
events.on(`${resource}.rescheduled`, async (model) => {
  ...
  this.#adapter.unschedule(this.#normalize({ model, key, resourceType: resource }, 'unscheduled'));
  this.#adapter.schedule(this.#normalize({ model, key, resourceType: resource }));
});
...
const bootstrap = !previousKey;
for (const model of scheduledResources[resourceType]) {
  this.#adapter.unschedule(this.#normalize({ model, key: unscheduleKey, resourceType }), { bootstrap });
  this.#adapter.schedule(this.#normalize({ model, key: currentKey, resourceType }));
}
```
**Flow:** `post/page.scheduled|rescheduled|unscheduled` events → fetch `internalKeys.get('ghost-scheduler')` → normalize job (unschedule path signs against `model.previous('published_at')`) → adapter call. Boot rebuild queries `status:scheduled+type:{post,page}` and re-enqueues everything.
**Invariant:** (1) The `event === 'unscheduled'` flag in #normalize switches to the PREVIOUS timestamp — the token must match the OLD queued URL or the adapter can't find the entry to remove. (2) Same-key rebuild (`bootstrap = !previousKey`) MUST pass `{bootstrap:true}` to unschedule: the default adapter implements unschedule as URL+time-keyed tombstones, and a same-URL tombstone would poison the about-to-be-scheduled identical job. Only key rotation (previousKey present) produces a different old URL where the tombstone correctly targets the stale entry. (3) Errors inside handlers are caught+logged per-event — a scheduling failure never fails the save that triggered it.
**Probe:** `grep -cF "const bootstrap = !previousKey" ghost/core/core/server/services/post-scheduling/post-scheduling.ts` → expect `1`; `grep -cE "events\.on\(" ghost/core/core/server/services/post-scheduling/post-scheduling.ts` → expect `3`; `grep -cF "model.previous('published_at')" ghost/core/core/server/services/post-scheduling/post-scheduling.ts` → expect `3` (normalize branch, extra.oldTime, plus previous() guard — verify count on pin); `grep -cF "status:scheduled+type:" ghost/core/core/server/services/post-scheduling/post-scheduling.ts` → expect `1`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ghost", query: "adapter rescheduleAll previousKey bootstrap", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt unschedule+schedule-as-reschedule with previous-timestamp signing and the bootstrap tombstone skip. Adapt the events bus; keep the two-mode distinction if your adapter dedupes by URL+time.
