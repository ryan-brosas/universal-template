<!-- capsule-v2 -->
# Event journal age-based cleanup — how does a live events database stay bounded without losing the aggregate picture of old activity?

**Source:** JetBrains dotMemory standalone distribution (proprietary distribution; study/reference use only, citations-only), pin `?@?` (not git-managed; identity = install self-hash `41e6f647…` + Codebase Memory generation 2026-08-24T13:53:49Z); Codebase Memory `jetbrains-dotmemory` (5,124 nodes / 5,117 edges, FULL). **Question:** When an app continuously records interval events forever, which eviction policy keeps memory flat while dashboards still show correct history?

## Precision-vs-aggregate journal with logarithmic age decay
**Path/Symbol:** `JetBrains.Common.Timeline.Framework.xml` `EventJournal.EventGroup.{Cleanup, CleanupWithDepthLimit, FindNewestTime, CountActualEntries}` (:44-89), `EventJournal.EventJournal.Cleanup(TimeSpan guaranteedWindow, Int32 ratio)` (:90-102); interface in `JetBrains.Common.Timeline.Framework.Interface.xml`: `EventJournal.IEventJournal.{Register, StopRunning, Remove, Query, GetLastValue}` (:52-82).
**Signature:** `Register(EventKind, EventValue, TimeSpan start, TimeSpan? end)` — null end = still running; `StopRunning(kind, value, start, end)` matches by kind+value+start; `Remove(...)` silently no-ops when not found (documented overload semantics); `Query(TimeSpan from, TimeSpan to, TimeSpan precision)`.
**Data Shape:** time-grouped tree; each group holds precise entries AND aggregated summaries (`GetTotalNumEvents` reads summaries); cleanup removes entries but never summaries; test introspection via `CountActualEntries(out eventCount, out groupCount, out eventSize, out groupSize)`.

### Decisive source
```text
Cleanup: "Removes precise event data from older groups while keeping aggregated
 values in upper-level groups. The older groups get more aggressive cleaning
 (cleaned at higher levels without traversing children). The newer groups get
 more delicate cleanup... depth of cleanup depends on the age of the group with
 non-linear proportion (logarithmic)."
guaranteedWindow: "Data within this time window from the newest time is
 guaranteed not to be cleaned. This defines the 'safe zone'."
ratio: "For each ratio-times the guaranteed window length, cleanup depth
 decreases by 1 level. A ratio of 2 means: at 2x window age, depth decreases
 by 1; at 4x, by 2; at 8x, by 3..."
IEventJournal.Query: "Precision defines the threshold when events with the same
 type will be aggregated into one... !!! Query should be disposed as soon as
 possible. Current implementation of thread safety delays adding new events
 while there are active queries." (queries walk the tree without copying)
CountActualEntries: "FOR TESTS ONLY ... Unlike GetTotalNumEvents which returns
 aggregated counters from summaries, this method counts real entries."
```

**Flow:** producers `Register` events (open-ended ones later closed by `StopRunning`) → periodic `Cleanup(guaranteedWindow, ratio)` walks groups: inside the safe zone nothing is touched; beyond it, cleaning starts at shallower depths for older groups (logarithmic decay), deleting precise entries while summary counters survive at upper levels → readers `Query(from,to,precision)` get same-type events folded into aggregates below the precision threshold → `FindNewestTime` trusts `mySummaryValues` (actual data extent), NOT the canonical group Range.
**Invariant:** aggregate answers stay stable across cleanup (only precision is lost, and only for old data); newest-time must be computed from real extents or cleaned regions report wrong ranges; query lifetime gates write throughput — long-held queries stall producers.
**Probe:** deterministic content assertions executed on both Framework XML files this pass: Cleanup logarithmic-depth text at `JetBrains.Common.Timeline.Framework.xml`:46-55/:92-101; safe-zone/ratio definitions :51-55 and :97-101; Query locking confession at `JetBrains.Common.Timeline.Framework.Interface.xml`:67-77; FOR-TESTS-ONLY marker :76-79/:104-108.
**Test-fixture path:** the docs themselves name the verification pattern — compare `CountActualEntries` (real entries) against `GetTotalNumEvents` (summaries) to prove cleanup reduced storage without changing aggregates.

## Get live surrounding code
**Retrieve:** executed live this pass:
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-dotmemory",
  query: "EventLog writer session timeline events", limit: 40 });
// → JetBrains.Common.Timeline.Framework.doc @ ...Framework.xml :2-133 and
//   ...Framework.Interface.doc @ ...Framework.Interface.xml :2-87 (both read in full).
```

## Verdict
Adopt age-decayed precision eviction (safe zone + ratio ladder over a grouped tree with surviving summaries), open-ended Register/StopRunning pairing, and precision-threshold queries that must be short-lived. Adapt grouping keys and summary math. Omit the RealtimeChart/viewport UI members sharing the assembly. Coverage caveat: documented API plane; behavioral claims are doc-grounded, checked `no_recorded_issue`.
