<!-- capsule-v2 -->
# fastify constraint-storage versioning — why does version matching move from wrapper filters into router constraints?

**Source:** nest MIT `master@4c38a5ab1`; Codebase Memory project `nest`. **Question:** When porting route versioning to a router with native constraint support, what must the adapter supply and how does the per-request version get derived?

## find-my-way constraints object: validate / storage / deriveConstraint / mustMatchWhenDerived
**Path/Symbol:** `packages/platform-fastify/adapters/fastify-adapter.ts:170-240 FastifyAdapter.versionConstraint`; stored via constructor `routerOptions.constraints` (:262-267); stamped by `applyVersionFilter :425-436`.
**Signature:** `applyVersionFilter(handler, version, versioningOptions): VersionedRoute` — returns the SAME handler function with `.version` attached (no wrapper).
**Data Shape:** `versionConstraint = { name: 'version', validate(value), storage(): {get/set/del/empty}, deriveConstraint(req), mustMatchWhenDerived: false }`. `this.versioningOptions` is captured ONCE — first `applyVersionFilter` call wins (`if (!this.versioningOptions)`) because the whole app shares one versioning config.

### Decisive source
```ts
// fastify-adapter.ts:182-186 — multi-version storage.get picks FIRST member present
get(version: string | Array<string>) {
  if (Array.isArray(version)) {
    return versions.get(version.find(v => versions.has(v))!) || null;
  }
  return versions.get(version) || null;
},
// :207-238 deriveConstraint — MEDIA_TYPE parses Accept ';'+key param,
// HEADER reads custom header (exact then lowercase), CUSTOM calls the
// extractor; missing value ⇒ VERSION_NEUTRAL for MEDIA_TYPE/HEADER,
// extractor's raw return for CUSTOM; undefined when no versioning configured
```

**Flow:** Boot: `applyVersionFilter` stamps `version` on the handler (never VERSION_NEUTRAL — `injectRouteOptions :863-865` excludes it) → `injectRouteOptions :895-920` merges handler `.version` + FASTIFY_ROUTE_CONSTRAINTS_METADATA into a `constraints` object passed to `instance.route()`. Request: find-my-way runs `deriveConstraint(req)`, looks the derived key up in the storage Map, matches routes whose registered constraint equals it. `mustMatchWhenDerived: false` lets non-versioned routes still match when a version WAS derived.
**Invariant:** This is a fundamentally different mechanism from express's wrapper-filter ladder (`handlerForCustomVersioning` etc. calling next on mismatch): fastify NEVER wraps the handler — the router itself does constraint dispatch. Porting one side's approach onto the other host loses either per-handler version arrays or first-present-member semantics. Multi-version registration relies on `set()` fanning each array member into its own Map entry.
**Probe:** `grep -n "mustMatchWhenDerived" packages/platform-fastify/adapters/fastify-adapter.ts` = exactly 1 at :239; `grep -n "version.find(v => versions.has(v))" packages/platform-fastify/adapters/fastify-adapter.ts` = 1 at :184. Direct-test coverage caveat: fastify-adapter.spec.ts covers only reply/mapException — constraint behavior pinned by source + consumer wiring.
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph '{"project":"nest","query":"applyVersionFilter handler version stamp","limit":4}'
```
Live-verified @4c38a5ab1: rank#2 `FastifyAdapter.applyVersionFilter packages/platform-fastify/adapters/fastify-adapter.ts 425-436`. NOTE: `versionConstraint` is a class PROPERTY, not a Function node — name_pattern queries return zero by construction; use the BM25 query above.

## Verdict
Adopt the constraint-object shape (validate/storage/derive triad + first-present-member get + VERSION_NEUTRAL fallbacks); adapt `deriveConstraint`'s three versioning-type branches to your header conventions; omit find-my-way internals. Contrast contract lives in `route-registration-layering.md` (express wrapper ladder). Coverage caveat: runner blocked; probes are deterministic greps.
