<!-- capsule-v2 -->
# Completable schema — how does argument autocompletion attach to a schema without breaking Standard Schema consumers?

**Source:** typescript-sdk MIT `main@cc4b4161`; Codebase Memory `mnt-hdd-utopia-inspo-mcp-typescript-sdk`. **Question:** How do you add a completion callback to a prompt/resource argument schema while keeping validation behavior untouched?

## Connected graph-selected seam
**Path/Symbol:** `packages/server/src/server/completable.ts` (whole, 74L): `COMPLETABLE_SYMBOL: unique symbol = Symbol.for('mcp.completable')` (:3), `completable<T extends StandardSchemaV1>(schema, complete)` (:51+).
**Signature:** `completable(schema: T, complete: CompleteCallback<T>): CompletableSchema<T>` — wraps the schema; the registry later unwraps via the global symbol.
**Data Shape:** `Symbol.for` (global registry) so separately-bundled SDK copies agree on "is this schema completable" without importing a shared class — the same cross-bundle trick as error branding.

### Decisive source
```ts
export const COMPLETABLE_SYMBOL: unique symbol = Symbol.for('mcp.completable');
export function completable<T extends StandardSchemaV1>(schema: T, complete: CompleteCallback<T>): CompletableSchema<T> { … }
```

**Flow:** author wraps an argument's zod/standard schema with `completable(s => …)` → server registers the prompt/resource → on `completion/complete` the registry walks declared arguments, checks `COMPLETABLE_SYMBOL in schema`, invokes the callback with the current value, and returns suggestions → validation still delegates to the wrapped schema unchanged.

**Invariant:** Completion is metadata BESIDE validation, never a replacement — the wrapper must stay a valid StandardSchemaV1. Global-registry symbol over import identity because prompts and their host may load different bundle copies (mirrors crossBundleBrand rationale).

**Probe:** deterministic source pin (74L whole-file read); upstream suite for this module not present at this pin — in-capsule coverage caveat recorded.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-mcp-typescript-sdk", query: "COMPLETABLE_SYMBOL completable", limit: 10, fields: ["signature", "name", "file"] });
```

**Verdict:** Adopt symbol-tagged wrapper for sidecar schema capabilities; adapt callback typing; omit if your framework carries completion out-of-band.
