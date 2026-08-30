<!-- capsule-v2 -->
# Cache-hint stamping seam — how does a 2026-only required field get filled without touching the legacy wire?

**Source:** typescript-sdk MIT `main@cc4b4161`; Codebase Memory `mnt-hdd-utopia-inspo-mcp-typescript-sdk`. **Question:** When a new revision REQUIRES `ttlMs`/`cacheScope` on cacheable results, how do you fill them from handler/config/defaults while keeping the old era byte-identical?

## Connected graph-selected seam
**Path/Symbol:** `packages/core-internal/src/shared/resultCacheHints.ts`: `attachCacheHintFallback`, `RESULT_CACHE_HINT_FALLBACK` symbol (:37-40 docblock), `CACHEABLE_RESULT_METHODS` closed list (:48-56), resolution ladder docblock (:1-27); consumption at the 2026 codec's `encodeResult`.
**Signature:** `isCacheableResultMethod(method: string): method is CacheableResultMethod` over the CLOSED six-method list (`tools/list`, `prompts/list`, `resources/list`, `resources/templates/list`, `resources/read`, `server/discover`).
**Data Shape:** Resolution order, most specific author first: (1) valid fields on the handler's result itself, (2) configured hint — per-registration then per-operation, combined per field, (3) conservative defaults `{ttlMs:0, cacheScope:'private'}`.

### Decisive source
```ts
// Symbol-keyed properties are never serialized to JSON, so attaching a hint
// can never change what a 2025-era response looks like on the wire: only the
// 2026-era codec reads (and removes) it while filling the required fields.
// The 2025-era codec has no cache code path at all.
```

**Flow:** era-blind server config attaches the hint under a module symbol on the result object → result flows through dispatch untouched (JSON never serializes symbols) → era codec's encode step: 2026 fills required fields from the ladder and REMOVES the symbol; 2025 encodes as identity, symbol invisible.

**Invariant:** The cacheable-operation list is CLOSED — no other operation's result ever receives cache fields from the SDK. Defaults are conservative: ttl 0 (immediately stale unless authored) and private scope (the spec's public grant "any client MAY serve any user" is too strong to infer). Suppression tests pin that a 2025 exchange carries NONE of the stamped vocabulary even with hints configured.

**Probe:** `packages/core-internal/test/wire/stampingSuppression.test.ts` :92 ("the 2025 codec encode is the identity for every cacheable operation, even with a configured hint attached"), :118 ("input_required resources/read … emitted without ttlMs/cacheScope"), :138 ("the cacheable-operation list is closed").

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-mcp-typescript-sdk", query: "RESULT_CACHE_HINT_FALLBACK CACHEABLE_RESULT_METHODS attachCacheHintFallback", limit: 10, fields: ["signature", "name", "file"] });
```

**Verdict:** Adopt symbol-carried config + era-gated encode-time filling for revision-required fields; adapt the hint ladder and defaults; omit the suppression tests only if you have equivalent byte-identity pins.
