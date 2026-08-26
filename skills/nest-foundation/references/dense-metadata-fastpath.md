<!-- capsule-v2 -->
# Dense ctor-metadata fast path — when can request-scoped resolution skip re-reading Reflect metadata entirely?

**Source:** nest MIT `master@61b03510`; Codebase Memory `nest`. **Question:** What is the exact density check that guards the fast path against feeding `undefined` to request-scoped factories?

## Injector.hasDenseCtorMetadata / loadCtorMetadata
**Path/Symbol:** `packages/core/injector/injector.ts:hasDenseCtorMetadata` (1150-1179), used at `resolveConstructorParams` (317-328); `loadCtorMetadata` (935-964).
**Signature:** `hasDenseCtorMetadata(wrapper, inject, metadata: InstanceWrapper[] | undefined): boolean`.
**Data Shape:** `metadata` is the wrapper's captured ctor-dependency InstanceWrapper array (`addCtorMetadata(index, wrapper)` writes by INDEX — sparse arrays possible).

### Decisive source
```ts
// The fast path requires a fully populated metadata array.
// While another request is still registering dependency metadata,
// sparse entries here would feed request-scoped factories `undefined`.
const expectedDepsLength = !isNil(inject)
  ? inject.length
  : wrapper.metatype ? this.reflectConstructorParams(wrapper.metatype).length : 0;
if (metadata.length !== expectedDepsLength) return false;
for (let index = 0; index < expectedDepsLength; index++) {
  if (metadata[index] === undefined) return false;   // holes disqualify
}
return true;
```

**Flow:** resolveConstructorParams under a non-static context → dense? reuse the CAPTURED wrappers via loadCtorMetadata (which resolves each host per effective inquirer) : fall back to full Reflect-metadata param walk.
**Invariant:** The fast path is only valid for non-static contexts AND complete arrays; length equality alone is insufficient — internal holes must be probed. Captured metadata also carries the resolution-time inquirer relationships, which re-reading class metadata would lose.
**Probe:** `packages/core/test/injector/injector.spec.ts::loadProvider` ("should not eagerly load a top-level transient provider during snapshot bootstrap" :328) and scoped-resolution specs in `packages/core/test/scope/`.
**Coverage caveat:** none recorded.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nest", query: "hasDenseCtorMetadata loadCtorMetadata addCtorMetadata", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the capture-once + density-gated fast path for hot request-scoped resolution; adapt to your metadata capture mechanism; omit if you have no per-request scope. Porting wrong: trusting array length without probing holes passes sparse arrays into factories as literal `undefined` arguments.
