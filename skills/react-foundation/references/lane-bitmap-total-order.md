<!-- capsule-v2 -->
# Lane bitmap total order — how does a bitmask encode priority, and when may an in-progress render be interrupted?

**Source:** facebook/react MIT `main@055705ca01766d2a4379261b05e7990a849bdedc`; Codebase Memory `react`. **Question:** How do lanes compare as priorities with pure integer ops, and what is the exact interrupt rule for a render already in progress?

## Bit position = priority; two's-complement and clz32 tricks
**Path/Symbol:** `packages/react-reconciler/src/ReactFiberLane.js` (`getHighestPriorityLane` :756–758, `getLanesOfEqualOrHigherPriority` :760–766, `getHighestPriorityLanes` :180–247, `getNextLanes` :249–361, `markStarvedLanesAsExpired` :541–588) + `packages/react-reconciler/src/ReactEventPriorities.js:22-67`.
**Signature:** `getHighestPriorityLane(lanes: Lanes): Lane`; `lanesToEventPriority(lanes: Lanes): EventPriority`; `higherEventPriority(a, b): EventPriority`.
**Data Shape:** `Lane` = single bit, `Lanes` = 31-bit mask. Bit order descending in priority: SyncLane (bit 1) > InputContinuous > Default > Gesture > Transition1–14 > Retry1–4 > hydration/Idle/Offscreen/Deferred. `EventPriority` is an **opaque alias for Lane**: Discrete=SyncLane, Continuous=InputContinuousLane, Default=DefaultLane, Idle=IdleLane.

### Decisive source
```js
// ReactFiberLane.js :756-758 — lowest set bit = highest priority lane.
export function getHighestPriorityLane(lanes: Lanes): Lane {
  return lanes & -lanes;
}
// :764-765 — right-fill mask of equal-or-lower priority:
const lowestPriorityLaneIndex = 31 - clz32(lanes);
return (1 << (lowestPriorityLaneIndex + 1)) - 1;
// ReactEventPriorities.js :30-35 — NoLane(0) means "no preference":
export function higherEventPriority(a: EventPriority, b: EventPriority): EventPriority {
  return a !== 0 && a < b ? a : b;
}
// ReactFiberLane.js :337-357 — THE interrupt rule:
if (wipLanes !== NoLanes && wipLanes !== nextLanes &&
    (wipLanes & suspendedLanes) === NoLanes) {
  const nextLane = getHighestPriorityLane(nextLanes);
  const wipLane = getHighestPriorityLane(wipLanes);
  if (
    // Tests whether the next lane is equal or lower priority than the wip
    // one. This works because the bits decrease in priority as you go left.
    nextLane >= wipLane ||
    // Default priority updates should not interrupt transition updates.
    (nextLane === DefaultLane && (wipLane & TransitionLanes) !== NoLanes)
  ) {
    return wipLanes;   // keep working on the existing tree. Do not interrupt.
  }
}
```

**Flow:** pending/suspended/pinged/warm lane sets on the root → `getNextLanes` picks the highest-priority unblocked group (`getHighestPriorityLanes` masks down to one group; sync lanes short-circuit first at :181–184) → interrupt check against the in-progress render's lanes → result drives both the sync/concurrent decision (workloop-timeslice-decision) and the Scheduler level (rootsched-lane-task-decision). Starvation escape: `markStarvedLanesAsExpired` walks pending lanes by index (`pickArbitraryLaneIndex = 31 - clz32`), stamps expiration times on CPU-bound lanes, and ORs expired ones into `root.expiredLanes` — deliberately EXCLUDING RetryLanes ("must always be time sliced, to unwrap uncached promises"; upstream TODO admits this path is untested).
**Invariant:** Priority comparison is pure integer arithmetic — never enumerate lanes. An in-progress render only yields its progress to a STRICTLY higher-priority lane (numeric bit less-than), with two semantic carve-outs layered on top: hydration lanes isolate, and Default never interrupts Transitions despite bit adjacency. Idle work never runs while non-idle work is pending (:279–282).
**Probe:** `packages/react-reconciler/src/__tests__/ReactUpdatePriority-test.js` FULL (:38–107 idle-vs-default paint split; :109–155 continuous-interrupts-transition via `unstable_runWithPriority(ContinuousEventPriority)`), plus `ReactFlushSync-test.js` :122–161 nearest-scope-wins nesting.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "react", query: "getHighestPriorityLane lanesToEventPriority higherEventPriority markStarvedLanesAsExpired", limit: 10 });
// Observed @ gen 2026-08-25T20:08:45Z: requestTransitionLane/flushSync family ranked
// in-file; lanesToEventPriority resolves at ReactEventPriorities.js :55-67.
```

## Verdict
Adopt "bit order IS priority" with `& -lanes`, right-fill masks, and numeric single-bit comparison for interruption decisions. Adopt retry-lane exclusion from expiry if your retries must stay time-sliced. Adapt the concrete lane groups to your domain. Omit parallel-transition splitting under `enableParallelTransitions` unless porting concurrent transition families. Coverage caveat: ReactFiberLane.js parse_partial flagged 1–1309 WHOLE FILE — every cited range was read directly from source; ReactEventPriorities.js read in full.
