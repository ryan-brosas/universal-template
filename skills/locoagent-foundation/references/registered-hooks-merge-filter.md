<!-- capsule-v2 -->
# registered-hooks merge-and-filter — SDK callbacks and plugin hooks share one registry; how do you evict only one kind?

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** Two hook sources (SDK `registerHookCallbacks` calls, native plugin loaders) append into one per-event registry — what are the merge, reset, and selective-eviction contracts?

## registerHookCallbacks / clearRegisteredPluginHooks: push-merge + pluginRoot-marked filtering
**Path/Symbol:** `src/bootstrap/state.ts`:`RegisteredHookMatcher` (`:27`), `registeredHooks` (`:166-167`), `registerHookCallbacks` (`:1419-1434`), `getRegisteredHooks` (`:1436-1440`), `clearRegisteredHooks` (`:1442-1444`), `clearRegisteredPluginHooks` (`:1446-1461`), `resetSdkInitState` (`:1463-1466`).
**Signature:** `registerHookCallbacks(hooks: Partial<Record<HookEvent, RegisteredHookMatcher[]>>): void`; `clearRegisteredHooks(): void` (nulls whole registry); `clearRegisteredPluginHooks(): void` (keeps callbacks only); `resetSdkInitState(): void`.
**Data Shape:** `Partial<Record<HookEvent, RegisteredHookMatcher[]>> | null`. Discriminator: callback matchers LACK `pluginRoot`; plugin-native matchers CARRY it. Null = "no registration yet" (distinct from empty).

### Decisive source
```ts
// :1426 — merge semantics documented in-source
// `registerHookCallbacks` may be called multiple times, so we need to merge (not overwrite)
for (const [event, matchers] of Object.entries(hooks)) {
  if (!STATE.registeredHooks[eventKey]) STATE.registeredHooks[eventKey] = []
  STATE.registeredHooks[eventKey]!.push(...matchers)      // APPEND, never assign
}
// :1451-1460 — selective eviction by structural discriminator
const filtered: Partial<Record<HookEvent, RegisteredHookMatcher[]>> = {}
for (const [event, matchers] of Object.entries(STATE.registeredHooks)) {
  // Keep only callback hooks (those without pluginRoot)
  const callbackHooks = matchers.filter(m => !('pluginRoot' in m))   // :1454
  if (callbackHooks.length > 0) filtered[event as HookEvent] = callbackHooks
}
STATE.registeredHooks = Object.keys(filtered).length > 0 ? filtered : null
```

**Flow:** SDK client init → `registerHookCallbacks(...)` appends per event → plugin load → plugin matchers join the same arrays → plugin reload/disable → `clearRegisteredPluginHooks()` rebuilds the structure keeping only `!pluginRoot` entries → full reconnect → `clearRegisteredHooks()` nulls everything → `resetSdkInitState()` also drops initJsonSchema with it.
**Invariant:** Registration is MERGE-not-overwrite (multiple SDK init calls must accumulate). Selective eviction uses a STRUCTURAL discriminator (`'pluginRoot' in m`) rather than parallel registries, so dispatch stays single-lookup; the rebuild normalizes back to `null` when nothing survives (preserving the null-vs-empty distinction that guards elsewhere check). Eviction is by MARKER, not by source tracking — no separate bookkeeping of who registered what.
**Probe:** Deterministic pins: `grep -n 'merge (not overwrite)' src/bootstrap/state.ts` → `1426:`; `grep -n "pluginRoot' in m" src/bootstrap/state.ts` → `1454:` (the filter site; note the source spells it `!('pluginRoot' in m)` so anchor on the inner substring); `grep -n 'registeredHooks = null' src/bootstrap/state.ts` → `1443:` AND `1465:` (two assignment sites).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "registerHookCallbacks clearRegisteredPluginHooks registeredHooks", limit: 10 });
```

## Verdict
Adopt single-registry hook accumulation with merge-on-register and marker-based selective eviction when two hook provenances share a dispatch path. Adapt the discriminator field to your matcher type. Omit the null-vs-empty subtlety only if your consumers never branch on it.
