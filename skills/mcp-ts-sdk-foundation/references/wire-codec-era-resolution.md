<!-- capsule-v2 -->
# Era-granular wire codec — how do five legacy revisions share one vocabulary while deletions stay physical?

**Source:** typescript-sdk MIT `main@cc4b4161`; Codebase Memory `mnt-hdd-utopia-inspo-mcp-typescript-sdk`. **Question:** How does an SDK version its wire schemas so a new protocol revision deletes methods without a side-table of special cases?

## Connected graph-selected seam
**Path/Symbol:** `packages/core-internal/src/wire/codec.ts`: `WireCodec` interface (:159-292), `codecForVersion` (:303-305), `classifiedWireEra` (:315-318), `isSpecRequestMethod` (:327-329), `MODERN_WIRE_REVISION` (:73).
**Signature:** `codecForVersion(version: string | undefined): WireCodec`; `ValidateOutcome<T> = {ok:true;value:T} | {ok:false;reason:'not-in-era'} | {ok:false;reason:'invalid';message:string}`.
**Data Shape:** Era resolution is many-to-one: ALL five legacy versions + `undefined`/unknown → the 2025 codec (hand-constructed instances default legacy); every modern revision (`>= 2026-07-28`, lexicographic ISO-date compare) → the 2026 codec. No side table — era is ordinary connection state.

### Decisive source
```ts
// Deletions are physical: registry membership is the deletion story. The
// 2026-era registry has no tasks/*, initialize, ping, logging/setLevel,
// resources/(un)subscribe … so an inbound era-mismatched method falls to
// −32601 by absence — even when a handler is registered.
export function codecForVersion(version: string | undefined): WireCodec {
    return version !== undefined && isModernProtocolVersion(version) ? rev2026Codec : rev2025Codec;
}
export function isSpecRequestMethod(method: string): boolean {
    return ALL_CODECS.some(codec => codec.hasRequestMethod(method));
}
```

**Flow:** inbound request → instance's negotiated codec → registry gate (`hasRequestMethod`) BEFORE handler lookup → params validation → outbound mirror: spec-universe methods die locally with typed `SdkError` before reaching the transport. Tri-state outcome preserves 'not-in-era' ≠ 'invalid' so the in-band fallback chain can fall through on absence.

**Invariant:** "The spec-method universe" is DERIVED as the union of all codecs' registries, never hand-curated — a custom handler for a deleted spec method serves only on the era that defines it; extension methods outside the universe stay era-blind. Collapsing not-in-era into invalid breaks fallback semantics. The 2026 codec strictly strips the deleted-field set (`execution.taskSupport`, `capabilities.tasks`) and stamps `resultType`; the 2025 codec has NO stamp code path (identity encode — never-stamp guarantee).

**Probe:** `packages/core-internal/test/wire/eraGates.test.ts` :120 ("answers tasks/get with −32601 BY ABSENCE even with a handler"), :309 ("2025 codec encodeResult is the identity"), :323/:353 (deleted-field strictness). Registry drift caught by `test/wire/registryDiffOracle.test.ts` (anchor-source diff oracle with owned seed decisions for the 2026 demotions).

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-mcp-typescript-sdk", query: "codecForVersion WireCodec validateRequest isSpecRequestMethod", limit: 10, fields: ["signature", "name", "file"] });
```

**Verdict:** Adopt era-as-codec with derived registries and physical deletion; adapt the tri-state validator seam to your schema stack; omit the per-revision wire modules unless you serve multiple revisions from one endpoint.
