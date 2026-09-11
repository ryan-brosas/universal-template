<!-- capsule-v2 -->
# post-compaction telemetry flag — how do you tell a compaction-induced cache miss apart from a TTL expiry?

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** Both compaction and cache TTL produce cold-cache API calls — what one-shot flag pattern separates them in telemetry without a state machine?

## markPostCompaction / consumePostCompaction: set-once, read-and-clear
**Path/Symbol:** `src/bootstrap/state.ts`:`pendingPostCompaction` (`:253-256`), `markPostCompaction` (`:769-773`), `consumePostCompaction` (`:775-781`). Correlated timestamps: `lastMainRequestId` (`:245-248`), `lastApiCompletionTimestamp` (`:249-252`, comment names the ~5min cache TTL).
**Signature:** `markPostCompaction(): void`; `consumePostCompaction(): boolean` (true ONCE after each compaction, then false until the next); `setLastMainRequestId(id)`, `setLastApiCompletionTimestamp(ts)`.
**Data Shape:** Single boolean + two scalar correlation slots. The flag is consumed by the FIRST successful API event after compaction.

### Decisive source
```ts
// :769-781
/** Mark that a compaction just occurred. The next API success event will
 *  include isPostCompaction=true, then the flag auto-resets. */
export function markPostCompaction(): void {
  STATE.pendingPostCompaction = true
}
/** Consume the post-compaction flag. Returns true once after compaction,
 *  then returns false until the next compaction. */
export function consumePostCompaction(): boolean {
  const was = STATE.pendingPostCompaction
  STATE.pendingPostCompaction = false
  return was
}
// :249-252 — the sibling timestamp's purpose
// Timestamp (Date.now()) of the last successful API call completion.
// Used to compute timeSinceLastApiCallMs in tengu_api_success for
// correlating cache misses with idle time (cache TTL is ~5min).
```

**Flow:** auto-compact or `/compact` completes → `markPostCompaction()` → next API call succeeds → logging layer calls `consumePostCompaction()` → emits `isPostCompaction=true` on exactly that one event → flag now false → later misses correlate with `timeSinceLastApiCallMs` (idle > ~5min TTL) instead → next compaction re-marks.
**Invariant:** Telemetry classification needs EXACTLY one marked event per cause; a sticky boolean would label every subsequent miss "post-compaction" and an edge-emitted event would need plumbing through the send path. Set-once/read-and-clear gives one-shot semantics with zero coupling — the sender doesn't know about compaction, it just reads a flag. The companion timestamp handles the OTHER cold-cache cause (TTL), so together two scalars classify all cache misses.
**Probe:** Deterministic pins: `grep -n 'flag auto-resets' src/bootstrap/state.ts` → `770:`; `grep -n 'Returns true once after compaction' src/bootstrap/state.ts` → `775:`; `grep -n 'pendingPostCompaction = false' src/bootstrap/state.ts` → `779:`; `grep -n 'cache TTL is ~5min' src/bootstrap/state.ts` → `251:`.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "consumePostCompaction markPostCompaction pendingPostCompaction", limit: 10 });
```

## Verdict
Adopt set-once/read-clear flags for one-event telemetry annotations at causal boundaries. Adapt event naming to your observability schema. Omit the idle-time twin if you don't track cache-TTL misses separately.
