<!-- capsule-v2 -->
# Session HTTP handler plane — how do you expose a long-lived session engine over typed HTTP without leaking engine error taxonomy or letting concurrent mutations corrupt state?

**Source:** opencode MIT `dev@03521003fafd`; Codebase Memory `opencode`. **Question:** Given an event-sourced session engine with its own error types (storage NotFound, busy-runner), how do you build the 28-endpoint HTTP adapter so clients see a stable 404/409/500 taxonomy and fire-and-forget prompt failures stay observable?

## Typed group + two-function error mapping ladder
**Path/Symbol:** `packages/opencode/src/server/routes/instance/httpapi/groups/session.ts` (`SessionPaths` :78-105, group middleware stack :452-454) + `handlers/session.ts` (`requireSession` :81-83, `promptAsync` :311-327, `share` :253-262, `updatePart` :396-412, `deleteMessage` :382-387) + `handlers/session-errors.ts` (whole, 18L).
**Signature:** `mapStorageNotFound<A,R>(Effect<A, StorageNotFoundError, R>) → Effect<A, ApiNotFoundError, R>`; `mapBusy<A,R>(Effect<A, Session.BusyError, R>) → Effect<A, ApiError.SessionBusyError, R>`; group = `HttpApiGroup.make("session").add(28 endpoints).middleware(InstanceContextMiddleware).middleware(WorkspaceRoutingMiddleware).middleware(Authorization)`.
**Data Shape:** API `SessionBusyError` carries `{sessionID, message}` and declares `httpApiStatus: 409` (errors.ts :116-124); `ApiNotFoundError` mirrors the legacy `{name:"NotFoundError", data:{message}}` shape. Busy-gated endpoints are exactly shell/revert/unrevert/deleteMessage (group error declarations :361/:374/:387/:413); prompt/command are NOT busy-gated — they queue inside the run-state kernel instead.

### Decisive source
```ts
// handlers/session-errors.ts — the whole ladder is two functions:
export function mapStorageNotFound<A, R>(self: Effect.Effect<A, StorageNotFoundError, R>) {
  return self.pipe(Effect.mapError((error) => ApiError.notFound(error.message)))
}
export function mapBusy<A, R>(self: Effect.Effect<A, Session.BusyError, R>) {
  return self.pipe(Effect.catchTag("SessionBusyError", (error) =>
    Effect.fail(new ApiError.SessionBusyError({ sessionID: error.sessionID,
      message: `Session is busy: ${error.sessionID}` }))))
}
// handlers/session.ts:311-327 — async prompt failure becomes an EVENT, not just a log:
yield* promptSvc.prompt({ ...ctx.payload, sessionID: ctx.params.sessionID }).pipe(
  Effect.catchCause((cause) => Effect.gen(function* () {
    yield* Effect.logError("prompt_async failed", { sessionID: ctx.params.sessionID, cause })
    yield* events.publish(Session.Event.Error, {
      sessionID: ctx.params.sessionID,
      error: new NamedError.Unknown({ message: Cause.pretty(cause) }).toObject(),
    })
  })),
  Effect.forkIn(scope, { startImmediately: true }),
)
return HttpApiSchema.NoContent.make()
```

**Flow:** every read handler runs `requireSession` (storage NotFound → 404) before touching sub-resources; mutating handlers wrap engine effects in `mapBusy` (engine BusyError → 409) or `mapStorageNotFound`; `prompt` runs synchronously and returns the created message as a one-shot JSON stream (`Stream.make(JSON.stringify(message))`, contentType application/json, :306 — not SSE); `promptAsync` forks into the request scope immediately, returns NoContent, and on ANY failure publishes `Session.Event.Error` over the bus so SSE subscribers observe it; `share`/`unshare` map failures to 500 InternalServerError deliberately (comment :255-259: storage/network failures are server-side, matching legacy ErrorMiddleware behavior — blanket 400 would misclassify them); `updatePart` rejects bodies whose id/messageID/sessionID disagree with the URL params (400, :404-409); `createRaw`/`forkRaw` use handleRaw so an empty body means "default payload" for legacy clients (:159-176, :218-232); `summarize` cleans pending revert state first and picks the compaction agent from the last user message's agent, falling back to the default (:277-280).
**Invariant:** Engine error types never cross the HTTP boundary un-mapped — storage NotFound is always 404, busy is always 409, share failures are always 500. A fire-and-forget prompt that fails MUST still emit a session-scoped error event; the HTTP response alone cannot carry it. Path/body ID agreement is checked for part updates.
**Probe:** `packages/opencode/test/server/httpapi-session.test.ts:238-248` ("maps busy sessions to public session busy errors" pins mapBusy → `_tag:"SessionBusyError"` with `Session is busy:` message); `:1020-1045` ("rejects part updates whose path and body ids disagree" pins the 400); `:1070-1085` (permissionRespond unknown ID → `_tag:"PermissionNotFoundError"`); source pin:
```bash
grep -n 'httpApiStatus: 409' packages/opencode/src/server/routes/instance/httpapi/errors.ts
grep -n 'forkIn(scope' packages/opencode/src/server/routes/instance/httpapi/handlers/session.ts
```
expect 2 + 1 hits (the two 409s are ConflictError :31 and SessionBusyError :122).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "opencode", query: "sessionHandlers mapStorageNotFound mapBusy promptAsync forkIn scope", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-function mapping ladder (storage-not-found→404, busy→409) as the adapter contract between any long-lived engine and its HTTP surface; adopt publish-to-bus as the only channel for async-fire-and-forget failures; adopt the deliberate 500-vs-400 split for server-side side effects (sharing/storage). Adapt the endpoint set and the one-shot-JSON "stream" response shape to your transport; omit opencode's legacy empty-body create/fork raw handlers unless you have pre-schema clients. Direct tests read whole (httpapi-session.test.ts 1090L); bun runner blocked at this checkout (no node_modules), probes are byte-exact greps.
