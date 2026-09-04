<!-- capsule-v2 -->
# Error-body shaping & preflight cache safety — how do you keep 4xx/5xx bodies small, SDK-parseable, and defect-only, while fixing a framework CORS Vary bug that poisons preflight caches?

**Source:** opencode MIT `dev@03521003fafd`; Codebase Memory `opencode`. **Question:** How should an HTTP layer convert defects and schema rejections into bounded, client-shaped errors, and what must it fix about generated CORS preflight headers?

## Defect-only boundary + reason cap + Vary merge
**Path/Symbol:** `.../middleware/error.ts` (whole, 43L), `.../middleware/schema-error.ts` (`REASON_LIMIT` :10, `schemaErrorLayer` :25-41), `.../middleware/cors-vary.ts` (whole, 29L); taxonomy at `.../errors.ts` (20 tagged classes, :3-193).
**Signature:** `errorLayer = HttpRouter.middleware((effect) => effect.pipe(Effect.catchCause(...)))`; `HttpApiMiddleware.layerSchemaErrorTransform(SchemaErrorMiddleware, (error, context) => ...)`.
**Data Shape:** legacy error body `{name, data:{message, kind?}}` (NamedError shape so SDK `wrapClientError` extracts `.data.message`); v2 `/api/*` body = typed `InvalidRequestError{_tag, message, kind}`; unknown-defect body carries a short correlation ref.

### Decisive source
```ts
// schema-error.ts:6-9 — why the cap exists, verbatim:
// Effect's Issue formatter recursively dumps the rejected `actual` value with
// no truncation, so a 5KB invalid array produces a ~360KB string. Cap to keep
// 4xx responses small and avoid mirroring entire request payloads (which may
// contain secrets) into the response body and log file.
const REASON_LIMIT = 1024
// cors-vary.ts:4-9 — the upstream bug, verbatim:
// effect-smol's HttpMiddleware.cors builds OPTIONS preflight responses by
// spreading allowOrigin() and allowHeaders() into the same record. Both set
// the `vary` key, so allowHeaders' `Vary: Access-Control-Request-Headers`
// overwrites allowOrigin's `Vary: Origin`. With dynamic origin echoing, the
// missing `Vary: Origin` lets shared caches reuse a preflight cached for one
// origin against a different origin.
```

**Flow:** the router-level error boundary catches ONLY Die reasons that are not already HttpServerResponse/HttpServerError/Respondable — typed failures stay on their declared error path (:6 comment "this boundary only replaces defect-only empty 500s"); config-shape defects become 400 JSON; anything else becomes 500 `{name:"UnknownError", data:{message:"Unexpected server error...", ref:"err_xxxxxxxx"}}` with the full cause logged under that ref (:28-39). Schema rejections: `/api/*` → typed InvalidRequestError failure; legacy routes → NamedError-shaped 400; both truncated to REASON_LIMIT with an ellipsis marker and logged as warnings. CORS: after every response, if dynamic allow-origin is set and Vary lacks Origin (and isn't `*`), merge `, Origin`.
**Invariant:** The boundary never converts typed failures; the cap is applied to the MESSAGE not the whole body; the Vary merge must not duplicate tokens or touch `*`. Error taxonomy: one `Schema.TaggedErrorClass` per condition with `httpApiStatus`, plus `ApiNotFoundError` mimicking the legacy `{name:"NotFoundError", data:{message}}` via `ErrorClass` for compat.
**Probe:** `packages/opencode/test/server/httpapi-schema-error-body.test.ts` — ":70 Payload rejection returns NamedError-shaped JSON", ":94 Query rejection kind=Query", ":110 v2 query rejection `_tag:"InvalidRequestError"`", ":124 rejected body never echoes back unbounded — 50_000-char input stays <2KB and absent from message", ":148 corrupted stored row (NaN tokens) surfaces field path `output`"; `httpapi-cors-vary.test.ts:28-62` pins merged Vary through the real server app; source pin:
```bash
grep -n "REASON_LIMIT = 1024" packages/opencode/src/server/routes/instance/httpapi/middleware/schema-error.ts
grep -n 'tokens.includes("origin")' packages/opencode/src/server/routes/instance/httpapi/middleware/cors-vary.ts
```
expect 1 hit each (:10, :24).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "opencode", query: "schema error middleware truncation reason limit cors vary origin preflight", limit: 8 });
```

## Verdict
Adopt defect-only boundaries with correlation refs, reason caps against reflection DoS/secret echo, dual-shape error bodies split by API generation, and the Vary merge fix for dynamic-CORS caches; adapt the config-error list to your host's failure modes; omit opencode's exact taxonomy names.
