<!-- capsule-v2 -->
# express not-found prefix skip — how does a root-mounted 404 handler avoid swallowing other apps' prefixed routes?

**Source:** nest MIT `master@4c38a5ab1`; Codebase Memory project `nest`. **Question:** When multiple Nest apps share one Express adapter, how must the unprefixed 404 handler be installed so it never intercepts requests belonging to a prefixed sibling app?

## registeredPrefixes set + segment-exact skip ladder inside the root middleware
**Path/Symbol:** `packages/platform-express/adapters/express-adapter.ts:167-198 setNotFoundHandler`; prefix recording `:169 registeredPrefixes.add(prefix)`; twin mount `setErrorHandler :155-165`.
**Signature:** `setNotFoundHandler(handler: Function, prefix?: string)`.
**Data Shape:** `registeredPrefixes = Set<string>` populated ONLY by prefixed `setNotFoundHandler` calls; the root middleware closure reads it at request time (late-binding — prefixes registered AFTER the root handler still get skipped).

### Decisive source
```ts
// express-adapter.ts:180-195
// When multiple apps share this adapter, a non-prefixed app's 404
// handler may be registered before a prefixed app's routes. Skip
// requests whose path belongs to another app's prefix so they can
// reach the correct route handlers further in the stack.
const path = req.originalUrl.split(/[?#]/)[0];
for (const registeredPrefix of this.registeredPrefixes) {
  // Match on full path segments only, so a prefix of "/api" does not
  // swallow unrelated paths such as "/apiary".
  if (
    path === registeredPrefix ||
    path.startsWith(`${registeredPrefix}/`)
  ) {
    return next();
  }
}
return (handler as any)(req, res, next);
```

**Flow:** Prefixed call ⇒ fresh Router with `router.all('*path', handler)` mounted at the prefix AND the prefix recorded. Root call ⇒ middleware that consults `registeredPrefixes` at request time: query/hash stripped, then for each recorded prefix an exact or `<prefix>/`-boundary match SKIPS this 404 (`next()`), letting later stack entries (the prefixed app's routes/handler) answer.
**Invariant:** Prefix matching is SEGMENT-boundary exact (`/api` vs `/apiary` comment is load-bearing) and evaluated per-request against mutable state — NOT captured at registration. A ported version that snapshots prefixes at mount time, matches by bare startsWith, or registers the root 404 without the skip loop will steal sibling apps' requests. Error-handler twin mounts at BOTH prefix and root unconditionally (:161-164 comment: routes outside the global prefix still need the exception layer).
**Probe:** Direct-test coverage caveat: express-adapter.spec.ts covers registerParserMiddleware/reply/mapException only — this seam is source-pinned. Deterministic anchors: `grep -n 'registeredPrefixes' packages/platform-express/adapters/express-adapter.ts` = exactly 3 lines (:60 field init, :169 prefixed-call add, :185 request-time loop); `grep -nF "router.all('*path'" packages/platform-express/adapters/express-adapter.ts` = 1 at :171.
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph '{"project":"nest","query":"setNotFoundHandler registeredPrefixes skip prefix","limit":5}'
```

## Verdict
Adopt the late-binding prefix-skip middleware verbatim (segment boundary + per-request read); adapt `'*path'` wildcard syntax to your router generation; omit express Router internals. Coverage caveat: runner blocked; anchors executed as greps.
