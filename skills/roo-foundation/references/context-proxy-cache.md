<!-- capsule-v2 -->
# ContextProxy state/secret cache — how do you cache VSCode global state + secrets while keeping writes and migrations correct?

**Source:** Roo-Code Apache-2.0 `main@b867ec9145750d0ae1ff7f02d35406e9bf2a0b16`; Codebase Memory `Roo-Code`. **Question:** How do you serve synchronous reads of async storage (state + secrets), route secret-keyed settings transparently, and migrate legacy fields without pinning users to stale defaults?

## Key-list-driven caches; isSecretStateKey routing; migration ladder at initialize
**Path/Symbol:** `src/core/config/ContextProxy.ts` (class :39-575; `initialize()` :57-96; condense-prompt migration `migrateOldDefaultCondensingPrompt` :156; provider sanitize `sanitizeProviderValues` :439-463 feeding `getProviderSettings` :416-437; `setProviderSettings` :466-488 clear-then-set; `setValue`/`getValue` routing :494-504; singleton `_instance`/`getInstance` :555-574).
**Signature:** `static async getInstance(context): Promise<ContextProxy>`; `getValues(): RooCodeSettings` (merge `{...globalState, ...secretState}`); `setValue<K>(key, value)` → secret vs global branch by `isSecretStateKey(key)`.
**Data Shape:** Caches keyed by exported key lists (`GLOBAL_STATE_KEYS`, `SECRET_STATE_KEYS`, `GLOBAL_SECRET_KEYS`); pass-through keys (`taskHistory`) bypass the cache entirely.

### Decisive source
```ts
// Migration that refuses to PIN users to an old default:
const isCustomized = legacyPrompt.trim() !== supportPrompt.default.CONDENSE.trim()
if (!currentSupportPrompts.CONDENSE && isCustomized) { /* copy into customSupportPrompts */ }
await this.originalContext.globalState.update("customCondensingPrompt", undefined) // always remove legacy
// v1-default detection via FINGERPRINTING, not exact match — clears saved old defaults so
// users actually RECEIVE the improved v2 default (whitespace-tolerant phrase check)
// Provider sanitize: unknown apiProvider values reset to undefined BEFORE schema.parse —
// "sanitized here to avoid repeated schema validation errors that can cause infinite update loops"
```
`setProviderSettings` first stamps ALL currently-set non-secret provider keys with `undefined` then spreads the new values — removed fields cannot linger. `openAiHeaders` is normalized to `{}` when empty "critical for proper serialization/deserialization through IPC". Every getter falls back to manual key-reduce when zod `parse` fails (schema drift must not brick reads). Export path omits task-history/meta keys and keeps only `source === "global"` custom modes.
**Flow:** construct empty → initialize loads state serially + secrets in parallel → run ordered migrations (image-gen, invalid provider, legacy condense, old default condense) → mark initialized → sync reads served from cache; writes go through setValue routing to storeSecret/updateGlobalState AND update cache.
**Invariant:** Cache is write-through (no staleness window); secrets never land in plain global state and vice versa; migrations are one-way, idempotent, and each individually try/caught so one failure can't block initialization; unknown providers are sanitized before parse to break validation-error update loops.
**Probe:** `src/core/config/__tests__/ContextProxy.spec.ts` (:99/:117/:129 cache vs pass-through reads, :154/:165 direct-to-context writes with pass-through bypass, :228-284 setValue/setValues routing incl. secret+global mix).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Roo-Code", query: "ContextProxy getValues setProviderSettings sanitizeProviderValues", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt key-list-driven caches, transparent secret routing, sanitize-before-parse (the infinite-loop comment is earned experience), and customization-preserving migrations. Adapt storage backends. The fingerprint-based old-default cleanup is optional but is what lets you ship better defaults without abandoning existing installs.
