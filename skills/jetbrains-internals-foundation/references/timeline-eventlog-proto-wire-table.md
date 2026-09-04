<!-- capsule-v2 -->
# Timeline events.proto wire table — what does a profiler's event-log stream actually consist of?

**Source:** JetBrains dotTrace standalone distribution (proprietary distribution; study/reference use only, citations-only), pin `?@?` (not git-managed; identity = root + generation 2026-08-24T13:55:36Z); Codebase Memory `jetbrains-dottrace`. **Question:** Which message families make up the captured-timeline wire format, and how do you reconstruct that table when only generated code docs ship?

## Twelve protobuf message families over one descriptor holder
**Path/Symbol:** `JetBrains.Common.Timeline.EventLog.xml` (whole file, 331 lines): `Protobuf.EventsReflection` + `EventsReflection.Descriptor`; messages `LogHeader`, `EventTypeDescriptor`, `EventPropertyDescriptor`, `StatisticsDescriptor`, `LayerDescriptor`, `StatisticsList`, `PeaksList`, `ThreadDescriptor`, `EventTreeHeader`, `LogIndex`, `StringEntry`.
**Signature:** every optional field carries the generated trio `<Field>FieldNumber` (F:), `Has<Field>` (P:), `Clear<Field>` (M:) — repeated fields (`Layers`, `EventTypes`, `Properties`, `StatisticDescriptors`, `StatisticPeaksIDs`, `NormalizedStatisticPeaksIDs`, `FilterEventTypes`, `Values`, `Threads`, `Headers`, `Peaks`) carry only the FieldNumber member.
**Data Shape:** reconstructed message table —
- `LogHeader{ProcessID, TicksPerSecond ("Frequency of ticks"), StartTick, Layers[], EventTypes[]}`
- `EventTypeDescriptor{ID, Properties[]}` / `EventPropertyDescriptor{Type, EnumValues, Name, ID}`
- `LayerDescriptor{ID, EventTypes[], StatisticDescriptors[], StatisticPeaksIDs[], NormalizedStatisticPeaksIDs[], Name, StorageType}`
- `StatisticsDescriptor{EventValueSource, Aggregation, EventType, EventPropertyIndex, FilterEventTypes[], ID, IsDefaultPropertyAggregator, HasIntepolationHelper}` (upstream typo "Intepolation" preserved)
- `StatisticsList{Values[]}` / `PeaksList{Values[]}`
- `ThreadDescriptor{ID, Type, NameStringId}` — thread names are string-table ids
- `EventTreeHeader{LayerID, ThreadID, RootChunkOffset, IsFirstEventTruncated, IsLastEventTruncated, Peaks, LeftTick, RightTick, Statistics}` — per-tree tick domain + truncation flags
- `LogIndex{Threads[], Headers[], EndTick}` / `StringEntry{Data}`

### Decisive source
```text
EventsReflection: "Holder for reflection information generated from events.proto"
EventsReflection.Descriptor: "File descriptor for events.proto"
LogHeader.TicksPerSecond: "Frequency of ticks"
EventTreeHeader.IsFirstEventTruncatedFieldNumber / IsLastEventTruncatedFieldNumber:
  the truncation state flagged in the Writer capsule is a first-class header field
ThreadDescriptor.NameStringId: names ride a string table (StringEntry{Data}), not inline
```

**Flow:** capture writes LogHeader (process, tick frequency, layer/event-type registries) → per-thread/per-layer EventTreeHeader chunks referenced by offset (`RootChunkOffset`) from LogIndex → statistics/peaks ride descriptor-driven value lists → all human-readable strings go through the StringEntry table.
**Invariant:** field presence is tri-state (Has*/Clear* vocabulary) — absence is meaningful; numeric ids (event types, layers, threads, properties) are registry-index references resolved through descriptors, so consumers must never hardcode id semantics; truncation flags live in the data itself, not side channels.
**Probe:** deterministic census executed this pass: full 331-line read of JetBrains.Common.Timeline.EventLog.xml enumerating every `member name="…"` — the twelve families above are exhaustive at this pin (recorded in verification.md).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-dottrace",
  query: "Timeline EventLog Writer TruncateFirstEvent section types", limit: 10 });
// → JetBrains.Common.Timeline.EventLog.doc @ JetBrains.Common.Timeline.EventLog.xml lines 2-331
//   (verified live); member-level text is not indexed — the table above comes from the direct read.
```

## Verdict
Adopt the shape for any captured-event stream: header registries (types/layers/strings) + offset-referenced per-stream trees with explicit tick domains and truncation flags. Adapt message fields to your event model; keep the generated Has/Clear presence discipline if using protobuf. Omit the dotTrace-specific statistics/aggregation descriptors unless porting profiling analytics.
