<!-- capsule-v2 -->
# Recent-snapshots lifecycle — how do you list user artifacts at startup without ever blocking boot on their I/O?

**Source:** JetBrains dotMemory standalone distribution (proprietary distribution; study/reference use only, citations-only), pin `?@?` (not git-managed; identity = install self-hash `41e6f647…` + Codebase Memory generation 2026-08-24T13:53:49Z); Codebase Memory `jetbrains-dotmemory` (5,124 nodes / 5,117 edges, FULL). **Question:** Which lazy-init, migration, and refresh moves keep a "recent files" list fast, honest about locked files, and testable?

## Lazy recent-artifact collection with off-thread refresh
**Path/Symbol:** `JetBrains.Common.SnapshotManagement.xml` (59L): `IRecentSnapshotsCollection.{summary, ForceInitializeAsync}` (:7-18), `RecentSnapshotsCollection.ResetInternal` (:19-23), `TryRemoveSnapshotFiles(FileSystemPath)` (:24-28), `RecentSnapshotIndexFilePathSettingsKey` (:29-33), `RecentSnapshotsStorage.{ResetInternal, EnqueueRefreshSnapshot, FixRecentSnapshotId}` (:34-50), `TempStorageCleanup.DeleteExpiredSnapshots(...)` (:51-57).
**Signature:** `Task ForceInitializeAsync()`; `bool TryRemoveSnapshotFiles(FileSystemPath)`; `void EnqueueRefreshSnapshot(IRecentSnapshot)`; `DeleteExpiredSnapshots(IRecentSnapshotsCollection, ISnapshotsSettingsProvider, ILogger)`.
**Data Shape:** settings keys historically stored `string IndexFilePath`, migrated to `guid` Id with backfill; each snapshot row carries existence/size/in-use state computed lazily.

### Decisive source
```text
IRecentSnapshotsCollection: "This component doesn't load data automatically in
 order to not impact the performance on app start. Call ForceInitializeAsync
 when you need it."
ForceInitializeAsync: "executes some code on the main thread, be careful waiting
 for it's completion using Task.Wait. See implementation for details."
TryRemoveSnapshotFiles: "Returns false if snapshot file(s) is locked"
EnqueueRefreshSnapshot: "updating its properties, such as whether the index file
 exists, the file size, and whether the file is in use ... on a background thread
 to avoid blocking the main thread."
FixRecentSnapshotId: "After changing settings key Id from 'string IndexFilePath'
 to 'string guid' we have to fill Id field with default value"
DeleteExpiredSnapshots: "This method is public because it's impossible to mock
 applicationWideSettings.GetValueProperty call. Consider to switch to use
 JetBrains.Common.Util.ISettings instead of ISettingsStore ... and fix test in a
 way it will test that this logic is called on lifetime termination"
```

**Flow:** startup constructs the collection WITHOUT touching disk → UI needing the list calls `ForceInitializeAsync` (which hops to the MAIN thread — awaiting it with `Task.Wait` from that same thread deadlocks; documented) → row state (exists/size/in-use) refreshes via background-thread queue → deletion is try-semantics: locked files return false instead of throwing → temp/expired snapshots are cleaned at lifetime termination → legacy settings keys are back-filled by `FixRecentSnapshotId` when the key schema changed.
**Invariant:** no disk I/O before first explicit demand; per-row state is eventually-consistent via refresh queue, never read synchronously for the list view; file removal must distinguish "deleted" from "locked"; settings-key migrations need explicit default-backfill or old installs lose rows.
**Probe:** deterministic content assertions executed this pass on `$REFERENCE_ROOT/dotmemory/JetBrains.Common.SnapshotManagement.xml`: lazy-init summary :8-10, Task.Wait caveat :14-17, locked-file false :26-27, background-refresh :40-44, guid migration :47-49, mockability confession :52-56 — verified by full 59-line read.

## Get live surrounding code
**Retrieve:** executed live this pass:
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-dotmemory",
  query: "SnapshotManagement storage descriptor external", limit: 25 });
// → JetBrains.Common.SnapshotManagement.doc @ JetBrains.Common.SnapshotManagement.xml :2-59 (read in full).
```

## Verdict
Adopt demand-driven initialization, queued background property refresh, try-style deletion under file locks, and explicit key-migration backfill. Adapt artifact taxonomy. Omit the ISettingsStore→ISettings refactor commentary except as a testability lesson: make cleanup reachable from tests without mocking static setting accessors.
