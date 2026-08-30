<!-- capsule-v2 -->
# Session-state snapshot deduplication — how do you persist mutable state to an append-only log without flooding it with identical entries?

**Source:** pi-model-router MIT `main@002b48f9bb03c068e0ef97eb230f49df57a24f93`; Codebase Memory `pi-model-router`. **Question:** How must a long-lived extension persist its mutable state to an append-only session entry log so that repeated no-op turns don't create unbounded duplicate entries?

## Zero-timestamp JSON snapshot comparison before append
**Path/Symbol:** `extensions/index.ts:persistState` (:99–135), `extensions/state.ts:buildPersistedState` (:22–49), `extensions/state.ts:isRouterPersistedState` (:8–20).
**Signature:** `persistState(): void` (closure); `buildPersistedState(routerEnabled, selectedProfile, pinnedTierByProfile, thinkingByProfile, debugEnabled, widgetEnabled, debugHistory, lastDecision, lastNonRouterModel, accumulatedCost): RouterPersistedState`; `isRouterPersistedState(value: unknown): value is RouterPersistedState`.
**Data Shape:** `RouterPersistedState` (types.ts :74–88) carries enabled, selectedProfile, pinTier?, pinByProfile?, thinkingByProfile?, debugEnabled?, widgetEnabled?, debugHistory?, lastPhase?, lastDecision?, lastNonRouterModel?, accumulatedCost?, timestamp. The snapshot for comparison zeroes ALL timestamps (top-level, nested lastDecision, each debugHistory element) so time-only changes don't trigger a write.

### Decisive source
```ts
const persistState = () => {
  const state = buildPersistedState(/* 10 args */);
  const snapshot = JSON.stringify({
    ...state,
    timestamp: 0,
    lastDecision: state.lastDecision
      ? { ...state.lastDecision, timestamp: 0 }
      : undefined,
    debugHistory: state.debugHistory?.map((decision) => ({
      ...decision,
      timestamp: 0,
    })),
  });
  if (snapshot === lastPersistedSnapshot) {
    return;  // no change → skip append
  }
  try {
    pi.appendEntry('router-state', state);
  } catch {
    return;  // stale runtime after session teardown
  }
  lastPersistedSnapshot = snapshot;
};
```
```ts
// state.ts — type guard checks only 3 fields (forward-compatible)
export const isRouterPersistedState = (value: unknown): value is RouterPersistedState => {
  if (typeof value !== 'object' || value === null) return false;
  const v = value as any;
  return (
    typeof v.enabled === 'boolean' &&
    typeof v.selectedProfile === 'string' &&
    typeof v.timestamp === 'number'
  );
};
```

**Flow:** build full state object → serialize to JSON with all timestamps zeroed → compare string to last persisted snapshot → if identical, return immediately (no I/O) → if different, call `pi.appendEntry('router-state', state)` inside try/catch (stale-runtime safety) → update cached snapshot. The type guard (`isRouterPersistedState`) deliberately checks only 3 required fields so future schema additions don't break readers of old entries.
**Invariant:** The append-only log grows only when meaningful state changes; timestamps never trigger a write; a failed append (stale runtime) is silently swallowed, not propagated.
**Probe:** `extensions/index.test.ts` :538–575 (two consecutive turn_end calls produce same appendEntry count — dedup works); `extensions/state.test.ts` :7–31 (type guard rejects non-objects, wrong types; accepts valid shape).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-model-router", query: "persistState appendEntry snapshot lastPersistedSnapshot", limit: 10 });
```

## Verdict
Adopt the zero-timestamp-snapshot-dedup pattern verbatim for any append-only persistence where the writer is called on every turn/tick; adapt the "which fields to zero" list to your volatile identifiers; omit nothing — the try/catch around append is essential for graceful degradation when the host runtime is already torn down. The minimal 3-field type guard is a forward-compatibility contract: new optional fields in the schema don't invalidate old entries.
