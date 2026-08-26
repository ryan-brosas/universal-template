<!-- capsule-v2 -->
# Snapshot section storage lifecycle — what write protocol keeps a multi-section binary snapshot crash-consistent and diagnosable?

**Source:** JetBrains dotTrace standalone distribution (proprietary distribution; study/reference use only, citations-only), pin `?@?` (not git-managed; identity = root + generation 2026-08-24T13:55:36Z); Codebase Memory `jetbrains-dottrace` (12,537 nodes, FULL mode). **Question:** How do you grow a binary snapshot from many typed sections without ever exposing a half-written section to readers — and how do you debug its I/O later?

## Sectioned snapshot kernel (documented API plane)
**Path/Symbol:** `JetBrains.Profiler.Snapshot.xml`: `Storage.Impl.WriteableSection.{Close,Dispose,OpenForReading}`, `Tools.SectionOffsetBinaryReader` / `Legacy.Writer.SectionOffsetBinayWriter` (metadata name `Write``1` — generic method), `Storage.Impl.LoggingSnapshotStorage`, `Converters.FuidToMetadataIdConverter.#ctor`.
**Signature:** `void OpenForReading(Lifetime)` — lifetime handed FROM the storage; `int Write<T>(BinaryWriter, SectionOffset<T>)` returns bytes written.
**Data Shape:** snapshot = sequence of typed sections addressed by encapsulated `SectionOffset{T}`; corruption flag per section; optional read/seek trace log beside the source file.

### Decisive source
```text
Dispose:      "If section is disposed before being closed, IsCorrupted is set to true
               and temp file is deleted"
Close:        "If section is closed correctly, it is added to storage with its lifetime
               (see OpenForReading(Lifetime))"
SectionOffset: "SectionOffset can be written to the stream without making
               SectionOffset<T>.Value public"
logread switch: "Log file is created only at the moment of storage disposal;
               LogFileName = SrcIndexFileName + '.log'"   // documented Read/Seek-per-reader trace grammar
FuidConverter: "convertor will be capable to convert fuids even if there will be
               no module section at all"
```

**Flow:** write into temp section → correct `Close()` registers the section into the storage (readers obtain it only via `OpenForReading(Lifetime from storage)`) → early `Dispose()` marks `IsCorrupted=true` AND deletes the temp file → offsets travel as opaque tokens, never raw ints → optional `logread` replays every Read/Seek with per-reader timings after disposal.
**Invariant:** a section becomes reader-visible ONLY through successful close; a crash mid-write can therefore leave an absent section, never a half-valid one; offset arithmetic stays internal so callers cannot corrupt addressing; converters tolerate missing module sections (forward/backward compatibility of partial snapshots).
**Probe:** deterministic content assertions on the doc plane: `grep -n "IsCorrupted" JetBrains.Profiler.Snapshot.xml` hits the Dispose member; `grep -n "logread"` anchors the logging contract; both cited by line number in verification.md.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-dottrace",
  query: "snapshot storage section", limit: 5 });
// → jetbrains-dottrace.JetBrains.Profiler.Snapshot.doc @ JetBrains.Profiler.Snapshot.xml (verified live);
//   member-text queries (e.g. "WriteableSection OpenForReading") return 0 — this index resolves at
//   assembly/file granularity, so cite the file node then read members directly.
```

## Verdict
Adopt the close-to-publish lifecycle (temp-write → explicit close → lifetime-bound read registration → corrupt-on-early-dispose), opaque typed offsets, and disposal-time I/O tracing keyed off a CLI switch. Adapt section taxonomy to your format. Omit the proprietary on-disk layout itself.