<!-- capsule-v2 -->
# Timeline event log protobuf schema — what wire schema makes an interval-event tree appendable during capture and randomly readable after it?

**Source:** JetBrains dotMemory standalone distribution (proprietary distribution; study/reference use only, citations-only), pin `?@?` (not git-managed; identity = install self-hash `41e6f647…` + Codebase Memory generation 2026-08-24T13:53:49Z); Codebase Memory `jetbrains-dotmemory` (5,124 nodes / 5,117 edges, FULL). **Question:** How is a profiler's timeline event log actually shaped on the wire — and where do "truncated edge" semantics live?

## events.proto descriptor census (generated Protobuf surface)
**Path/Symbol:** `JetBrains.Common.Timeline.EventLog.xml` `Protobuf.*` members (:7-329): `LogHeader{ProcessID,TicksPerSecond,StartTick,Layers,EventTypes}`; `LayerDescriptor{ID,EventTypes,StatisticDescriptors,StatisticPeaksIDs,NormalizedStatisticPeaksIDs,Name,StorageType}`; `StatisticsDescriptor{Aggregation,EventValueSource,EventType,EventPropertyIndex,FilterEventTypes,ID,IsDefaultPropertyAggregator,HasIntepolationHelper}`; `ThreadDescriptor{ID,Type,NameStringId}`; `EventTreeHeader{LayerID,ThreadID,RootChunkOffset,IsFirstEventTruncated,IsLastEventTruncated,Peaks,LeftTick,RightTick,Statistics}`; `LogIndex{Threads,Headers,EndTick}`; `StringEntry{Data}`.
**Signature:** generated accessors per field: `<F>FieldNumber` const, `Has<F>` / `Clear<F>` pairs for singular fields (repeated fields have neither).
**Data Shape:** header carries capture clock (`TicksPerSecond`, `StartTick`) + process identity; layers own typed event types and statistic descriptors; each thread×layer gets an EventTreeHeader pointing at its chunked tree (`RootChunkOffset`) with tick bounds (`LeftTick`/`RightTick`) and explicit first/last-truncation flags; strings are interned in a side table referenced by `NameStringId`.

### Decisive source
```xml
<member name="P:...LogHeader.TicksPerSecond"><summary>Frequency of ticks</summary>
<member name="F:...EventTreeHeader.IsFirstEventTruncatedFieldNumber">
<member name="F:...EventTreeHeader.IsLastEventTruncatedFieldNumber">
<member name="F:...ThreadDescriptor.NameStringIdFieldNumber">
Writer-side test seam, JetBrains.Common.Timeline.EventLog.Writer.xml :7-11:
EventSessionWriter.TruncateFirstEvent(EventTreeInfo, out ulong lastTick, ulong tick):
"This is used only in tests to simulate StartSession after some interval event
 is already been active."
```

**Flow:** session opens → LogHeader pins pid + tick clock → events stream into per-thread/per-layer trees whose chunks grow behind `RootChunkOffset` → a tree that starts mid-interval (session attached to an already-running event) records `IsFirstEventTruncated=true` — exactly the state `TruncateFirstEvent` exists to fabricate in tests; end-of-session mirror flag `IsLastEventTruncated` closes the other edge → `LogIndex` binds threads to headers plus a global `EndTick`.
**Invariant:** time axis is RELATIVE to a declared clock (TicksPerSecond+StartTick), never wall-clock; edge truncation must be an explicit schema flag because consumers cannot infer it from data; display names travel by string-table id, not inline.
**Probe:** executed this pass — `grep -c "FieldNumber" JetBrains.Common.Timeline.EventLog.xml` = **44** distinct generated field-number constants matching the census above; truncation-flag ↔ writer-seam linkage verified by direct read of both files (:264-281 and :7-15).
**Cross-product proof:** `JetBrains.Common.Timeline.EventLog.Interface.xml` :7-16 documents `JetBrains.DotTrace.Features.Processing.Timeline.V2.EventCSwitch` ("Structures of CSwitch etw event") INSIDE dotMemory's install — one shared timeline kernel serves both products.

## Get live surrounding code
**Retrieve:** executed live this pass:
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-dotmemory",
  query: "EventLog writer session timeline events", limit: 40 });
// → JetBrains.Common.Timeline.EventLog.doc @ JetBrains.Common.Timeline.EventLog.xml :2-331
//   (+ .Interface :2-19, .Writer :2-17); member text read directly from those ranges.
```

## Verdict
Adopt the schema shape: declared tick clock, layer/event-type descriptors, string interning, chunk-offset trees with EXPLICIT edge-truncation flags. Adapt message vocabulary to your domain. Omit ETW-specific CSwitch payloads. Caveat: schema reconstructed from generated-code docs; `.proto` source itself is not shipped.
