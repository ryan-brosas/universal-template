<!-- capsule-v2 -->
# Session state and reload survival — what lives per-conversation, what survives a hot reload, and how do heavyweight caches stay collectible?

**Source:** pi-fovea MIT `DETACHED@217a103`; Codebase Memory `pi-fovea`. **Question:** Extension modules get re-evaluated on resume/fork/new/reload — which caches must die with the conversation and which must ride through, and where do 80-vector Float64 stacks go when evicted?

## Focus sessions die on reset; baselines ride a versioned global slot
**Path/Symbol:** `src/core/session.ts:getSession/resetSessions/FOCUS_T0/TK_ORDER` (:27-60); `src/core/sync.ts:syncBaselineStore/BASELINE_STATE_VERSION` (:47-86); eviction `src/core/ops.ts:evictLru` (:97-104).
**Signature:** `getSession(root): FoveaSession` (LRU ≤ ROOT_CACHE_LIMIT, touch-to-refresh); `syncBaselineStore(): Map<string, SyncBaseline>` via `Symbol.for("pi-fovea:sync-baselines")` global slot.
**Data Shape:** `FoveaSession = {root, t (FOCUS_T0=2), seeds, seedNote, focusKey, scope, disclosed: Set<nodeId>, tk: Float64Array[], tkKey}`. focusKey = `version:sortedSeeds:scopeKey` — disclosure belongs to ONE focus key; a new seed/scope resets to sharp context.

### Decisive source
```ts
// `/new` and friends: same repo, fresh eyes.
export const resetSessions = (): void => {
  // A fresh conversation cannot reuse disclosure or Chebyshev vectors; drop
  // the entries outright so large Float64Array stacks become collectible.
  sessions.clear();
};
// Hot-reload survival: `/fovea reload` re-evaluates this module in the same
// process, so a plain module-level Map would drop every charged ledger and
// the next drift would re-fire as a first disclosure. Park the baselines on
// a registered global symbol; the store OUTLIVES the module instance. The
// version stamp keeps shape changes safe: a mismatched slot degrades to a
// cold store instead of corrupting verdict math.
const BASELINES_SLOT = Symbol.for("pi-fovea:sync-baselines");
if (held && held.v === BASELINE_STATE_VERSION) return held.map;
```

**Flow:** session_start / resume / fork / new / reload → epoch bump + `resetSessions()` + `resetSyncBaselines()` (disclosure and baselines are session-local and must never cross that boundary) → but the baseline MAP OBJECT itself is fetched from the global slot so an in-process reload keeps charged ledgers (a reload no longer replays cascades as first disclosures). Resident RepoStates evict LRU-style at ROOT_CACHE_LIMIT with their inflight promises and persist timers cleared.
**Invariant:** Disclosure/Chebyshev/session scope are conversation-scoped; the verdict ledger is process-scoped with a shape-version gate (mismatch → cold store, never corruption). Cached tk vectors belong to one focusKey; dwell extends them under the same key (`+ext`) rather than resetting.
**Probe:** `tests/sync.test.ts` "hot-reload handoff" describe — "baselines survive a module reload via the global store" (vi.resetModules + re-import returns the SAME map) and "a mismatched shape version degrades to a cold store".

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pi-fovea", query: "syncBaselineStore getSession resetSessions", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-tier state taxonomy (session-local disclosure vs process-global versioned ledgers), Symbol.for parking for hot-reload survival, and drop-don't-clear eviction of heavy vector caches. Adapt the slot name/version to your extension. Omit nothing else.
