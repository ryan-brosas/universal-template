<!-- capsule-v2 -->
# Branch-safe state restore with legacy migration — how do you recover persisted state from an append-only session branch without corrupting on schema drift?

**Source:** pi-model-router MIT `main@002b48f9bb03c068e0ef97eb230f49df57a24f93`; Codebase Memory `pi-model-router`. **Question:** How must a long-lived extension restore its state from a session's append-only entry log when the log may contain multiple entries, stale data, or entries written by an older version of the extension?

## findLast + type-guard + field-by-field apply + legacy pinTier migration
**Path/Symbol:** `extensions/index.ts:restoreStateFromSession` (:287–380), `extensions/state.ts:isRouterPersistedState` (:8–20).
**Signature:** `restoreStateFromSession(ctx: ExtensionContext): Promise<void>` (closure).
**Data Shape:** Scans `ctx.sessionManager.getBranch()` (array of `CustomSessionEntry`), filters to `type==='custom' && customType==='router-state'`, maps to `.data`, applies `.findLast(isRouterPersistedState)` — the LAST valid entry wins (latest state). Each field is applied with `??` fallback to current in-memory value.

### Decisive source
```ts
const entries = ctx.sessionManager.getBranch() as CustomSessionEntry[];
const savedState = entries
  .filter((entry) =>
    entry.type === 'custom' && entry.customType === 'router-state',
  )
  .map((entry) => entry.data)
  .findLast((data) => isRouterPersistedState(data));

if (isRouterPersistedState(savedState)) {
  selectedProfile = resolveProfileName(currentConfig, savedState.selectedProfile);
  routerEnabled = savedState.enabled;
  if (savedState.pinByProfile) {
    Object.assign(pinnedTierByProfile, savedState.pinByProfile);
  }
  if (savedState.thinkingByProfile) {
    Object.assign(thinkingByProfile, savedState.thinkingByProfile);
  }
  // LEGACY MIGRATION: old single-pin → new per-profile map
  if (savedState.pinTier && selectedProfile) {
    pinnedTierByProfile[selectedProfile] = savedState.pinTier;
  }
  debugEnabled = savedState.debugEnabled ?? debugEnabled;
  widgetEnabled = savedState.widgetEnabled ?? widgetEnabled;
  debugHistory = savedState.debugHistory
    ? [...savedState.debugHistory].slice(-MAX_DEBUG_HISTORY)
    : [];
  lastNonRouterModel = savedState.lastNonRouterModel ?? lastNonRouterModel;
  accumulatedCost = savedState.accumulatedCost ?? 0;
  lastDecision = savedState.lastDecision;
}
```

**Flow:** (1) capture ctx, reload config from disk; (2) wait 50ms for registry sync after re-registration; (3) reset volatile state IN-PLACE (delete keys from pin/thinking maps to keep object references intact for other closures); (4) scan branch entries → filter by customType → findLast valid; (5) apply fields with `??` defaults; (6) migrate legacy `pinTier` (single value) into `pinByProfile[selectedProfile]` (per-profile map); (7) re-validate active profile exists in config (`ensureValidActiveRouterProfile`); (8) attempt `setModelInternally(routerModel)` — on failure: notify + disable router; on success: sync thinking level from lastDecision; (9) persist final state.
**Invariant:** The LAST valid entry always wins (not first); missing optional fields fall back to current in-memory values (never undefined); legacy single-pin format is transparently migrated to per-profile map; a failed model restore degrades to disabled+warning, never throws.
**Probe:** `extensions/index.test.ts` :102–133 (basic restore sets model), :346–383 (failed setModel → notify + enabled:false), :385–426 (unavailable model → notify + setHiddenThinkingLabel), :428–459 (legacy pinTier:'medium' → pinByProfile:{balanced:'medium'}), :461–498 (lastDecision.thinking synced via setThinkingLevel).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-model-router", query: "restoreStateFromSession getBranch router-state findLast", limit: 10 });
```

## Verdict
Adopt the findLast+type-guard+field-by-field-apply pattern verbatim for any append-only state recovery; adopt the in-place key deletion (not reassignment) for maps shared across closures; adopt the legacy-migration-as-if-block pattern (old field → new field, guarded by presence check); adapt the 50ms registry-sync delay to your host's registration latency; omit nothing — the ensureValidActiveRouterProfile re-check after restore is essential because config may have changed between sessions.
