<!-- capsule-v2 -->
# Internal action guard flags — how do you prevent infinite feedback loops when an extension both observes and acts on host events?

**Source:** pi-model-router MIT `main@002b48f9bb03c068e0ef97eb230f49df57a24f93`; Codebase Memory `pi-model-router`. **Question:** When an extension calls the host's `setModel()` or `setThinkingLevel()` internally, the host fires a `model_select` / `thinking_level_select` event back — how do you break that loop without losing legitimate external changes?

## Boolean guard flags set before/after internal host calls; event handlers early-return on flag
**Path/Symbol:** `extensions/index.ts:setModelInternally` (:51–63), `extensions/index.ts:setThinkingLevelInternally` (:65–74), guard check in `model_select` handler (:471), guard check in `thinking_level_select` handler (:516).
**Signature:** `setModelInternally(model: NonNullable<ExtensionContext['model']>): Promise<boolean>`; `setThinkingLevelInternally(level: ThinkingLevel): void`.
**Data Shape:** Two closure-scoped booleans: `isInternalModelSwitch`, `isInternalThinkingChange`. Set to `true` before the host call, reset to `false` in `finally` (guaranteed reset even on throw). Event handlers check the flag as their FIRST condition after the init guard.

### Decisive source
```ts
const setModelInternally = async (model) => {
  isInternalModelSwitch = true;
  try {
    return await pi.setModel(model);
  } catch {
    // Extension context may be stale after session teardown.
    return false;
  } finally {
    isInternalModelSwitch = false;
  }
};

// In model_select handler:
pi.on('model_select', async (event, ctx) => {
  ensureInitializedFromContext(ctx);
  if (!isInitialized || isInternalModelSwitch) return;  // ← GUARD
  // ... rest of handler only runs for EXTERNAL model changes
});

// In thinking_level_select handler:
pi.on('thinking_level_select', (event, ctx) => {
  ensureInitializedFromContext(ctx);
  if (!isInitialized || !routerEnabled || !selectedProfile) return;
  if (isInternalThinkingChange) return;  // ← GUARD
  // ... apply user's thinking change as all-tier override
});
```

**Flow:** Router decides to switch model → sets `isInternalModelSwitch=true` → calls `pi.setModel(model)` → host fires `model_select` event synchronously/asynchronously → handler checks flag → sees `true` → returns immediately (no re-routing, no re-persist, no status update) → `finally` resets flag to `false` → next EXTERNAL model change proceeds normally. Same pattern for thinking level. The try/catch around `pi.setModel` handles stale-runtime teardown (returns `false` instead of throwing).
**Invariant:** Internal actions NEVER trigger their own event handlers; the flag is ALWAYS reset (finally block); external user actions are never suppressed (flag is only true during the synchronous internal call window). A stale runtime that throws on setModel is caught and returns false, not propagated.
**Probe:** `extensions/index.test.ts` :223–244 (model_select before init is no-op — isInitialized guard), :187–221 (external non-router select correctly records lastNonRouterModel and persists — proves external events still work). The internal-guard path itself is implicitly tested: if the guard failed, the restore test (:102–133) would loop infinitely on setModel.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-model-router", query: "isInternalModelSwitch setModelInternally model_select guard", limit: 10 });
```

## Verdict
Adopt the boolean-flag-in-finally pattern verbatim for any extension/plugin that both observes and acts on the same host event bus; adapt the flag names to your domain; omit nothing — the finally-reset is critical (a missed reset on exception would permanently suppress all future external events). If your host supports a "source" or "origin" parameter on events, prefer that over a global flag; but when it doesn't, this pattern is the minimal correct solution.
