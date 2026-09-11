<!-- capsule-v2 -->
# Lazy schema warm-up — when should wire-schema construction move from request time to module scope?

**Source:** typescript-sdk MIT `main@cc4b4161`; Codebase Memory `mnt-hdd-utopia-inspo-mcp-typescript-sdk`. **Question:** On isolate-based edge runtimes that bill per-request CPU, how do you keep first-request validation from paying one-time construction cost?

## Connected graph-selected seam
**Path/Symbol:** `packages/core-internal/src/wire/preload.ts`: `preloadSchemas` (:92-102) + economics docblock (:46-91); layers: `rev2025-11-25/buildSchemas.ts`, `rev2026-07-28/buildSchemas.ts` (memoized factories), registry/inputRequired/codec warm functions above them.
**Signature:** `preloadSchemas(): void` — synchronous, idempotent; every layer is a memo so the first call does all work and later calls return immediately.
**Data Shape:** No return value and no new objects: forcing the memos preserves reference identity — lazy consumers and preloaded consumers pull the SAME codec/registry objects.

### Decisive source
```ts
// On platforms that bill request CPU but not module evaluation — isolate-based
// edge/serverless runtimes such as Cloudflare Workers — the trade inverts:
// module-scope work runs during isolate warm-up outside any request …
// The packages' own workerd shims already do this.
export function preloadSchemas(): void {
    buildSchemas2025();
    buildSchemas2026();
    warmRegistryMaps2025();      // (the 2026 registry has no map memo of its own)
    warmInputSchemaMaps2026();
    warmWireResultSchemas2026();
}
```

**Flow:** process-per-invocation runtime (CLI/dev server) → stay LAZY (module evaluation IS startup latency; most short-lived processes never validate both eras). Isolate runtime (Workers) → call `preloadSchemas()` at module scope → construction lands in isolate warm-up outside billed requests. Each package bundles its own schema copy, so warm the ones you import.

**Invariant:** Idempotency + reference identity are load-bearing: warming must never fork a parallel graph of schemas or validation behavior diverges between cold and warm paths. Lazy-by-default is correct on process-per-invocation runtimes — eager construction there is pure added boot latency.

**Probe:** `packages/core-internal/test/wire/preload.test.ts` :31 ("returns void, synchronously"), :35 ("idempotent: repeated calls keep serving the same memoized objects"), :50 ("warms the same memos the lazy consumers pull through (reference identity, no parallel graph)").

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-mcp-typescript-sdk", query: "preloadSchemas buildSchemas2025 warmRegistryMaps", limit: 10, fields: ["signature", "name", "file"] });
```

**Verdict:** Adopt the memo-identity-preserving warm-up pattern for any lazily-built validator stack with a per-request billing model; adapt which layers you warm to your own memo set; omit the workerd shim auto-wiring unless you ship platform shims too.
