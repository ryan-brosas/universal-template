<!-- capsule-v2 -->
# Memory-mapped section storage V10 bridge — how do multiple processes share append-only sections through one file without readers ever seeing uncommitted bytes?

**Source:** JetBrains dotMemory standalone distribution (proprietary distribution; study/reference use only, citations-only), pin `?@?` (not git-managed; identity = install self-hash `41e6f647…` + Codebase Memory generation 2026-08-24T13:53:49Z); Codebase Memory `jetbrains-dotmemory` (5,124 nodes / 5,117 edges, FULL). **Question:** What is the reserve→commit protocol over memory-mapped pages that makes concurrent section growth safe — and why does the install ship a second `_v10` native library?

## Two-phase Free/Ready commit over paged sections
**Path/Symbol:** `JetBrains.Common.MemoryMappedStorage.xml` (410L): `TimelineApi.ISectionMemory.{Allocate, AllocateMax, TakeOrAllocateMax, SetReadySize, FixSize}` (:49-90), `IMemoryMappedSectionData.{FreePosition, TrySetFreePosition, SetReadyPosition}` (:143-171), `IReadonlySectionsEnumerator.MoveNext` pollable semantics (:283-289), `MemoryMappedStorageFactory.{Create,OpenRead,OpenReadWrite}(Lifetime, path|SafeFileHandle, startPosition)` (:329-401), `MemoryMappedStorageV10.Impl.Interop.SectionData` adapter (:402-408).
**Signature:** `long Allocate(long size, out long allocatedOffset)`; `bool TrySetFreePosition(ref long expectedFreePosition, int delta)`; `long SetReadyPosition(long readyPosition)` returns previous value.
**Data Shape:** one file hosts a sections list; each section = optional header + data description (element size, segment alignment bit-shift, preferred region pages; 0 = fixed size); positions are element-indexed; views map page-aligned regions.

### Decisive source
```text
TrySetFreePosition: "Tries to update free offset. Can fail spuriously, even if
 free offset equals to expected"                       // CAS-style reserve
SetReadyPosition: "Commits segments data before readyPosition ... Must be greater
 or equal then current ReadyPosition ... lower or equal then current FreePosition"
Read side: ReadyPosition = "first element after last commited data. Data before
 this position can be read."
IReadonlySectionsEnumerator: "not inherited from IEnumerator because ... can
 return elements after the last element if appeared ... MoveNext ... can be called
 after returning false [to poll for new sections]"; yielded elements "must be
 disposed"; ISectionsEnumeratorCurrent.CreateSection "Can be called only once!!!"
Factory remarks (×3 overloads): "MemoryMappedStorage is not thread-safe when shares
 the one or uses the duplicated file handle" + "doesn't take ownership over given
 handle, the caller is responsible to dispose passed handle."
V10 adapter :402-408: "Adapts the V1 native library (which uses UInt32 offsets) to
 the ISectionData interface (which uses long). Narrowing casts (long->UInt32) on
 input are safe because the V1 snapshot format structurally limits section sizes
 to 4 GB."
```

**Flow:** writers reserve space by CAS-bumping `FreePosition` (`TrySetFreePosition`, spurious failure = retry) → write into mapped pages → publish by advancing `ReadyPosition` monotonically up to Free → readers only ever consume below Ready, so torn writes are structurally invisible → consumers enumerate sections with a POLLING loop (MoveNext-after-false waits for late-appearing sections) and must dispose each; header/data descriptions are create-once (second creation fails) → `FixSize` seals a section against further allocation. The `_v10` native twin exists because V10 readers drive the OLD V1 native lib through this long↔UInt32 adapter: the on-disk legacy format is 4 GB-capped per section.
**Invariant:** Ready ≤ Free at all times and both move forward only; commit is monotonic advance, never rewrite; storage opened on a shared/duplicated handle is single-thread-only; handle ownership stays with the caller.
**Probe:** executed this pass — `find <root> -name "*MemoryMappedStorage*"` confirms BOTH native generations on disk: `linux-x64/libJetBrains.Common.MemoryMappedStorageApi.so` AND `linux-x64/libJetBrains.Common.MemoryMappedStorageApi_v10.so` (Pass 1's twin note CONFIRMED); same probe exposes `JetBrains.Profilers.Common[.Util].MemoryMappedStorage.JetMetadata.sstg` at root — the JetMetadata `.sstg` symbol tables are MemoryMappedStorage-format files, which is why two variants exist (with/without the Util layer). Doc assertions verified by full read of :143-171/:283-289/:329-408.

## Get live surrounding code
**Retrieve:** executed live this pass:
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-dotmemory",
  query: "MemoryMappedStorage section v10", limit: 20 });
// → JetBrains.Common.MemoryMappedStorage.doc @ JetBrains.Common.MemoryMappedStorage.xml :2-410 (read in full).
```

## Verdict
Adopt the two-phase Free/Ready protocol, polling non-IEnumerator section enumeration, create-once headers, and explicit handle-lending rules. Adapt page sizing/alignment vocabulary. Omit the 4 GB V1 constraint if starting fresh — it is a legacy-format fact, not a design goal. Record note: Pass 1's on-disk `_v10` twin claim is CONFIRMED by this pass's name-based locate; the :402-408 adapter doc explains WHY both native generations ship (V10 managed readers still drive the UInt32 V1 native ABI).
