<!-- capsule-v2 -->
# Timeline EventLog versioned-section stack — how does a captured timeline stay readable across format evolution without corrupting old snapshots?

**Source:** JetBrains dotTrace standalone distribution (proprietary distribution; study/reference use only, citations-only), pin `?@?` (not git-managed; identity = root + generation 2026-08-24T13:55:36Z); Codebase Memory `jetbrains-dottrace`. **Question:** Which versioning + section-id discipline lets you change a converted-snapshot format while old captures stay interpretable?

## Converted-version counter + never-reuse raw-section ids
**Path/Symbol:** `JetBrains.Common.Timeline.DAL.xml`: `TimelineConvertedSnapshotVersion`, `TimelineSectionTypes` (whole file, 21 lines); test-only truncation hook in `JetBrains.Common.Timeline.EventLog.Writer.xml:7-15`: `EventSessionWriter.TruncateFirstEvent`; ETW input struct in `JetBrains.Common.Timeline.EventLog.Interface.xml:7-12`: `EventCSwitch`.
**Signature:** `TimelineConvertedSnapshotVersion` — an increment-on-format-change counter; `TruncateFirstEvent(EventTreeInfo, UInt64@ lastTick, UInt64 tick)`; `EventCSwitch` — struct mirror of the Windows ETW CSwitch schema.
**Data Shape:** converted data lands in a FOLDER whose NAME embeds the version counter; the raw-section registry is append-only with an `ObsoleteSection` marker for retired ids.

### Decisive source
```text
TimelineConvertedSnapshotVersion: "Every time you change something in the format of
  the converted snapshot, increment this counter… The version is included in the name
  of the folder with the converted data. Such update will force a viewer to reprocess
  the snapshot, as it wouldn't be able to locate converted folder."
TimelineSectionTypes: "If some of the raw sections become obsolete - it should remain
  in the list so that it's id is not reused in the future. One can use ObsoleteSection
  tag for it… Obsolete converted sections can be removed given
  TimelineConvertedSnapshotVersion.Version is updated"
EventSessionWriter.TruncateFirstEvent: "This is used only in tests to simulate
  StartSession after some interval event is already been active."
EventCSwitch: "Structures of CSwitch etw event" (links the MS ETW CSwitch spec)
```

**Flow:** capture writes raw sections under stable numeric ids → conversion produces derived data in a version-stamped folder → viewer looks up `folder-with-my-version`; miss ⇒ reprocess from raw sections → when the CONVERTED format changes, bump the counter (old converted folders are simply abandoned, raw stays) → when a RAW section retires, mark it `ObsoleteSection` but keep its id allocated forever.
**Invariant:** two independent lifetimes — raw-section ids are NEVER reused (append-only registry), converted formats are invalidated by counter bump (cache-by-name). The truncation hook exists ONLY for tests simulating mid-interval attach; it is not a production API despite shipping in the writer's public doc plane.
**Probe:** deterministic line-pinned content assertions: Writer.xml L9 ("used only in tests"), DAL.xml L9-11 (version-in-folder-name), DAL.xml L16 (`ObsoleteSection` non-reuse rule) — all read directly this pass and recorded in verification.md.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-dottrace",
  query: "Timeline EventLog Writer TruncateFirstEvent section types", limit: 10 });
// → JetBrains.Common.Timeline.EventLog.Writer.doc @ JetBrains.Common.Timeline.EventLog.Writer.xml
//   + JetBrains.Common.Timeline.EventLog.doc (331-line member plane) — verified live.
```

## Verdict
Adopt the dual-lifetime scheme: immutable id allocation for raw capture data, name-embedded version counters for derived caches. It decouples "format changed" from "data lost". Adapt folder-naming to your cache layout and keep the obsolete-tag discipline even if your registry is code. Omit the ETW-specific struct unless porting Windows trace ingestion.
