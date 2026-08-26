<!-- capsule-v2 -->
# Staleness tracking ledger — how do you know a file in context was just edited behind your back?

**Source:** Roo-Code Apache-2.0 `main@b867ec9145750d0ae1ff7f02d35406e9bf2a0b16`; Codebase Memory `Roo-Code`. **Question:** How does an agent notice out-of-band user edits to files it already read, without re-reading everything?

## FileContextTracker: append-only entries + self-edit suppression + get-and-clear drains
**Path/Symbol:** `src/core/context-tracking/FileContextTracker.ts:23-280`; types `FileContextTrackerTypes.ts` (RecordSource: `read_tool|file_mentioned|roo_edited|user_edited`, record_state `active|stale`); consumer wiring via `getEnvironmentDetails`/condense file list.
**Signature:** `trackFileContext(filePath, operation)`, `addFileToFileContextTracker(taskId, filePath, source)`, `getAndClearRecentlyModifiedFiles(): string[]`, `markFileAsEditedByRoo(filePath)`, `dispose()`.
**Data Shape:** Per-task metadata JSON `{ files_in_context: [{ path, record_state, record_source, roo_read_date?, roo_edit_date?, user_edit_date? }] }` — NEW entry per event; prior entries for that path are demoted `active → stale`.

### Decisive source
```ts
watcher.onDidChange(() => {
  if (this.recentlyEditedByRoo.has(filePath)) {
    this.recentlyEditedByRoo.delete(filePath)      // OWN edit: swallow the echo
  } else {
    this.recentlyModifiedFiles.add(filePath)       // USER edit: surface to the model
    this.trackFileContext(filePath, "user_edited")
  }
})
// roo_edited sets read+edit dates NOW, arms checkpointPossibleFiles,
// and pre-seeds recentlyEditedByRoo BEFORE the write lands
```
WeakRef to the provider keeps the tracker from pinning the extension host in memory; all metadata IO degrades to defaults on error (read → `{files_in_context: []}`).

**Flow:** any tool/mention/edit touching a full file calls trackFileContext → append entry + lazily create a per-file watcher → watcher events classify edits as self vs user via the suppression set → environment details inject "user modified this file" warnings → condense pulls `getFilesReadByRoo(sinceTs?)` (recency-sorted, deduped). Drains (`getAndClear*`) empty their sets so each turn reports changes exactly once.
**Invariant:** Self-edit echo suppression must be armed BEFORE Roo writes, or every own-edit masquerades as a user edit and pollutes context; the ledger is append-only so staleness history survives restarts.
**Probe:** No dedicated spec dir at this HEAD (coverage caveat) — behavior pinned indirectly via condense suite fixtures and `src/core/environment/getEnvironmentDetails.ts` consumption.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Roo-Code", query: "FileContextTracker markFileAsEditedByRoo recentlyModifiedFiles", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt append-only staleness entries + self-echo suppression + drain-on-report semantics; it feeds both stale-context warnings and condense's folded-context input. Adapt RecordSource vocabulary and storage location. Omit vscode.FileSystemWatcher mechanics for non-VS Code hosts (swap in chokidar).
