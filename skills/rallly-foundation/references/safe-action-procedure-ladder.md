<!-- capsule-v2 -->
# Safe-action procedure ladder — how does a second mutation framework coexist with tRPC, and why does session revocation happen server-side here but not there?

**Source:** Rallly AGPL-3.0 `main@1b085700afec1dd5aa0eca419133dcba9bcdc9d6`; Codebase Memory `rallly`. **Question:** What is the next-safe-action equivalent of the tRPC procedure ladder, and what does its error handler know that the tRPC one cannot assume?

## actionClient → authActionClient → adminActionClient with code-collapsing error boundary
**Path/Symbol:** `apps/web/src/lib/safe-action/server.ts` (whole file, 129L): `createRateLimitMiddleware` (16–44), `actionClient` + `handleServerError` (46–101), `authActionClient` (103–118), `adminActionClient` (120–129).
**Signature:** `authActionClient.metadata({actionName}).inputSchema(schema).action(fn)`; ctx gains `{ user, ability }`.
**Data Shape:** every thrown error collapses to a STRING code returned to the client: `AppError.code`, a better-auth `APIError.status` allowlist, `"UNAUTHORIZED"` for InvalidSessionError, or `"INTERNAL_SERVER_ERROR"`.

### Decisive source
```ts
if (error instanceof InvalidSessionError) {
  // Expected condition, not reported to Sentry. Unlike server
  // components, server actions can write cookies, so revoke the
  // stale session directly instead of delegating to the client
  // error boundary.
  try {
    await signOut();
  } catch {
    // The error response must be returned regardless
  }
  return "UNAUTHORIZED" as const;
}
```
```ts
export const authActionClient = actionClient.use(async ({ next }) => {
  const user = await getCurrentUser();
  if (!user) {
    throw new AppError({ code: "UNAUTHORIZED", message: "You are not authenticated." });
  }
  const ability = defineAbilityFor(user);
  return next({ ctx: { user, ability } });
});
```

**Flow:** base client runs maintenance availability (`assertAppAvailable`) → auth layer re-resolves the user from the request cookie store and attaches a CASL-style `ability` to ctx → admin layer re-checks `role !== "admin"` → handler runs. On ANY throw, handleServerError classifies: expected session/maintenance errors skip Sentry; unexpected ones are captured with the actionName tag; the client receives only a string code, never messages or stacks.
**Invariant:** the decisive asymmetry vs tRPC (see `procedure-access-ladder`): tRPC's mutationSessionGuard cannot clear the stale cookie because it doesn't own the response — it throws UNAUTHORIZED and lets middleware/sign-out flows handle it; server actions CAN write cookies, so this ladder revokes the dead session inline before answering. A porter who copies either side verbatim into the other transport gets either unrevokable zombie sessions or a crash on cookie writes outside a mutable response context.
**Probe:** deterministic grep anchors (executed): `grep -c 'InvalidSessionError' apps/web/src/lib/safe-action/server.ts` → 2 (import + instanceof); `grep -n 'server actions can write cookies' apps/web/src/lib/safe-action/server.ts` → line 54. No dedicated upstream test — composition is source-pinned.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "rallly", query: "authActionClient handleServerError signOut", limit: 5 });
```

## Verdict
Adopt the ladder shape and the string-code error envelope verbatim; adapt rate-limit backend and ability library; omit Sentry if absent. Cross-ref: consumer-side projection of these codes is `safe-action-error-code-projection`; tRPC twin is `procedure-access-ladder`.
