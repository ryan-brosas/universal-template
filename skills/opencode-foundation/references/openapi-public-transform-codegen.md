<!-- capsule-v2 -->
# Public OpenAPI transform + SDK codegen — how do you keep a generated client stable while the typed spec tightens, and what must a spec-transform pipeline repair?

**Source:** opencode MIT `dev@03521003fafd`; Codebase Memory `opencode`. **Question:** How does a team regenerate an SDK from an Effect-HttpApi-derived OpenAPI document while freezing legacy wire shapes and surviving upstream generator bugs?

## Spec transform annotation + fail-loud post-patches
**Path/Symbol:** `packages/opencode/src/server/routes/instance/httpapi/public.ts` (`PublicApi` :530-537, `matchLegacyOpenApi` :82-178, `fixSelfReferencingComponents` :424-458, `stripOptionalNull` :461-495, `QueryParameterSchemas` :58-74) + `packages/sdk/js/script/build.ts` (whole, 119L).
**Signature:** `PublicApi = OpenCodeHttpApi.annotateMerge(OpenApi.annotations({transform: matchLegacyOpenApi}))`; build = `bun dev generate > openapi.json` → prune → hey-api `createClient` → three assertive patches → prettier/tsc.
**Data Shape:** transform mutates the raw spec in place (paths/components); query overrides keyed by `"${METHOD} ${path} ${param}"`.

### Decisive source
```ts
// public.ts:84-89 — repairing an Effect deduplicator bug with a regenerated spec:
// Effect's multi-document JSON Schema deduplicator can produce self-referencing
// component schemas (e.g. {"$ref":"#/components/schemas/X"} as the definition
// of X itself) ... Resolve these by inlining the actual schema from any parent union
const raw: OpenApiSpec = OpenApi.fromApi(OpenCodeHttpApi)   // :452 — ground truth re-generation
if (rawSchemas[name]) schemas[name] = rawSchemas[name]      // :456
// build.ts:97-102,106-113 — post-codegen patch that MUST apply or the build dies:
const sseTypesPatched = sseTypesSource.replace(
  "=> Promise<ServerSentEventsResult<TData, TError>>",
  "=> Promise<ServerSentEventsResult<TData>>",
)
if (sseTypesPatched === sseTypesSource) throw new Error(`SseFn patch did not apply; ...`)
```

**Flow (the transform ladder):** fix self-referencing components ⇒ strip `{type:"null"}` arms from every component/body/response (`Schema.optional` emits anyOf[T,null]; legacy SDK wants plain T) ⇒ PascalCase component renaming + numbered-twin collapse via description-blind canonicalized JSON equality (`stableSchema`) ⇒ hand override table (additionalProperties loosening, nullable fields) ⇒ inject legacy `BadRequestError`/`NotFoundError` NamedError components ⇒ delete security schemes. Per-operation: legacy ops lose `requestBody.required`, `security`, and 401s (auth is runtime middleware, not legacy metadata) while `/api/*` v2 ops KEEP them; the three SSE routes get explicit `text/event-stream` response schemas because HttpApi lacks first-class SSE responses; message/command POST responses are forced to `{info, parts}`.
**Flow (codegen):** dump spec via CLI ⇒ delete unreachable `SessionNext\w+1` twins by `$ref` reachability walk ⇒ hey-api typescript/sdk/client-fetch plugins into `src/v2/gen` ⇒ patch history `limit`/`after` string→number in BOTH types.gen and sdk.gen (regex miss throws) ⇒ SseFn TReturn patch (hey-api passes endpoint TError into the AsyncGenerator TReturn slot; `.return()` consumers type-check against the wrong shape) ⇒ prettier/tsc.
**Invariant:** Every post-codegen regex patch fails the build when it stops matching — silent no-op patches are forbidden because they hide upstream generator drift. The v2/legacy split is enforced by tests: v2 keeps auth metadata and never rewrites errors to legacy components.
**Probe:** `packages/opencode/test/server/httpapi-public-openapi.test.ts` — ":104 names the v2 event union" (no V2Event1 collision; V2EventStream contentMediaType pins SSE schema), ":119 preserves /api auth responses" (401 + `security: []` on every v2 op), ":175 does not rewrite /api endpoint errors to legacy error components", ":189 built-in error allowlist gate"; source pin:
```bash
grep -n "transform: matchLegacyOpenApi" packages/opencode/src/server/routes/instance/httpapi/public.ts
grep -c "did not apply" packages/sdk/js/script/build.ts
```
expect 1 hit + 3 hits.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "opencode", query: "openapi public legacy transform stripOptionalNull self-referencing components", limit: 8 });
```

## Verdict
Adopt the annotate-with-transform pattern for spec compatibility and fail-loud post-codegen patches as drift alarms; adapt the specific repair ladder to whatever your generator emits (re-run its raw output as ground truth like fixSelfReferencingComponents does); omit opencode's exact legacy component tables.
