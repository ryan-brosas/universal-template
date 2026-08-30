<!-- capsule-v2 -->
# Typed API route assembly — how do you compose one Effect HttpApi tree from protocol-owned groups, legacy groups, and per-tier middleware without coupling the spec to server services?

**Source:** opencode MIT `dev@03521003fafd`; Codebase Memory `opencode`. **Question:** How does a server compose a single typed OpenAPI surface from (a) a standalone protocol package's group factories and (b) local legacy groups, while keeping middleware placement in the spec and concrete services on the server side?

## Three-level composition
**Path/Symbol:** `packages/opencode/src/server/routes/instance/httpapi/api.ts` (`ServerApi` :48-52, `RootHttpApi` :54-59, `InstanceHttpApi` :61-77, `OpenCodeHttpApi` :79-94) + `packages/protocol/src/api.ts` (`makeApiFromGroup` :26-64, `makeApi` :66-76).
**Signature:** `HttpApi.make(name).addHttpApi(subApi).middleware(M)`, `makeApi({definitions, locationMiddleware, sessionLocationMiddleware}) → HttpApi`.
**Data Shape:** `RootHttpApi` = control + control-plane + global groups with `SchemaErrorMiddleware` + `Authorization`. `InstanceHttpApi` = 15 legacy groups + SchemaError. `OpenCodeHttpApi` = Root ⊕ EventApi ⊕ Instance ⊕ ServerApi(protocol) ⊕ PtyConnectApi, annotated with `AdditionalSchemas` (EventSchema union auto-built from `EventManifest.Latest` with literal-type discriminators, plus InstanceDisposed/Question/Credential/Integration/SkillV2 shapes).

### Decisive source
```ts
// packages/protocol/src/api.ts:25 — the ownership split, verbatim comment:
// Protocol owns middleware placement, while Server injects concrete keys so Core service identities stay downstream.
.add(makeSessionGroup(sessionLocationMiddleware))          // :41 — group factory takes Context.Keys,
.add(LocationGroup.middleware(locationMiddleware))          // :39 — not service instances
// api.ts:85 — AdditionalSchemas makes event payloads part of the generated SDK even though events ride raw SSE:
.annotate(HttpApi.AdditionalSchemas, [EventSchema, Question.Replied, /* ... */])
```

**Flow:** protocol factories attach location/session-location middleware *keys* per group ⇒ opencode's `ServerApi = makeApi({...})` passes its own concrete Context.Keys (`LocationMiddleware`, `SessionLocationMiddleware`) ⇒ all sub-APIs merge into `OpenCodeHttpApi` ⇒ `server.ts createRoutes()` mounts each tier as a separate `HttpApiBuilder.layer` plane with DIFFERENT provided stacks (auth variants, workspaceRouting, instanceContext, schemaError), merged via `Layer.mergeAll`.
**Invariant:** Middleware *placement* is portable spec metadata; middleware *implementations* are server-injected. Never import Core service identities from the protocol package. The `/doc` endpoint serves `OpenApi.fromApi(PublicApi)` through a `lazy()` wrapper — spec generation must not run at module load for CLI/script processes, and caching the response caches the serialized Uint8Array.
**Probe:** `packages/opencode/test/server/httpapi-public-openapi.test.ts:73-85` ("includes plugin-facing core schemas" pins AdditionalSchemas components exist); layer-order pin at `server.ts:307-311` (Observability-last comment citing #34730):
```bash
grep -n "Must stay last" packages/opencode/src/server/routes/instance/httpapi/server.ts
```
expect exactly 1 hit.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "opencode", query: "makeApi makeApiFromGroup protocol middleware placement", limit: 8 });
```

## Verdict
Adopt the protocol-package/group-factory split (spec owns shape+middleware slots; host injects services) and lazy /doc generation; adapt group names and the location-middleware key set to your host; omit the specific legacy/v2 dual-generation history if you have no compat surface to freeze.
