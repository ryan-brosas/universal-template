<!-- capsule-v2 -->
# Scheduler publish tolerance ladder — when must a fired schedule job publish, no-op, or refuse?

**Source:** Ghost MIT `main@81292b004cf59591f03d7dbe01f28f31c09ee813`; Codebase Memory `ext-ghost`. **Question:** How does the server-side endpoint decide whether an incoming scheduler ping should actually publish?

## publish(resourceType, id, force, options)
**Path/Symbol:** `ghost/core/core/server/services/posts/post-scheduling.js:exports.publish` (:29–83; NO_OP sentinel :17–23; `exports.handleCacheInvalidation` :85–103).
**Signature:** `async (resourceType: 'post'|'page', id: string, force: boolean, options) => { scheduledResource, preScheduledResource } | NO_OP`.
**Data Shape:** tolerance = `config.get('times').publishAPostBySchedulerToleranceInMinutes` (minutes); NO_OP = `{scheduledResource: null, preScheduledResource: null}`.
### Decisive source
```js
if (publishedAtMoment.diff(moment(), 'minutes') > publishAPostBySchedulerToleranceInMinutes) {
  return NO_OP;                                   // too early — job is stale after reschedule-later
}
if (publishedAtMoment.diff(moment(), 'minutes') < publishAPostBySchedulerToleranceInMinutes * -1 &&
    force !== true) {
  return Promise.reject(new errors.NotFoundError({ message: messages.jobPublishInThePast }));
}
```
**Flow:** read resource (NotFoundError ⇒ deleted-while-queued ⇒ NO_OP, 2xx) → within +tolerance? publish via `api[resourceType].edit({status:'published'})` → earlier than −tolerance WITHOUT force ⇒ NotFoundError "Use the force flag to publish a post in the past" (scheduler retries with force added by _pingUrl) → edit result returned so the controller sets cache-invalidation headers.
**Invariant:** Three-way ladder is deliberate: early ⇒ silent no-op (2xx empty list so scheduler marks done and does NOT retry); late-without-force ⇒ ERROR not silent skip (a genuinely dropped publish must be visible/retried); late-with-force ⇒ publish. The controller's permission stage tolerates ONLY NotFoundError (deleted resource) so NoPermissionError still propagates. Cache invalidation matrix: draft→published or unpublished-from-published ⇒ invalidate `/*`; draft/scheduled transitions otherwise ⇒ per-URL `/p/<uuid>/` family.
**Probe:** `grep -cF "publishAPostBySchedulerToleranceInMinutes" ghost/core/core/server/services/posts/post-scheduling.js` → expect `4` (decl + two diffs + comment-free count verified at pin); `grep -cF "* -1 &&" ghost/core/core/server/services/posts/post-scheduling.js` → expect `1`; direct test suite: `ghost/core/test/legacy/api/admin/schedules.test.js`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ghost", query: "publishAPostBySchedulerToleranceInMinutes", limit: 5, fields: ["signature", "name", "file"] });
```
**Drift note (2026-08-24):** BM25 tokenizes on Function nodes only — this free-function symbol surfaces under `handleCacheInvalidation` queries (`posts-service.PostsService.handleCacheInvalidation` is a DIFFERENT method for normal edits; don't confuse them). Retrieve by exact name or fall back to reading the file.

## Verdict
Adopt the ± tolerance ladder with force-flag escape and error-not-silent late publishes. Adapt the config knob; pair it with a client that adds force on retry-after-past like scheduling-default._pingUrl does.
