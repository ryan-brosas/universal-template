<!-- capsule-v2 -->
# stream-progress-emit — how do you convert native ingestion progress into UI updates without re-rendering on every chunk?

**Source:** oh-my-pi MIT `main@2b66ee69f2`; Codebase Memory `oh-my-pi`. **Question:** What change-detection gate decides that a progress tick is worth an emit, and what does the emitted update carry?

## streamContents emit closure
**Path/Symbol:** `packages/coding-agent/src/cli/git-tui/state.ts` (`GitFileModel.streamContents` `emit` closure).
**Signature:** `streamContents(file: ChangedFile, onProgress: (update: FileStreamUpdate) => void, signal?: AbortSignal): Promise<FileContents>`.
**Data Shape:** `FileStreamUpdate { oldLineOffset, oldLines, newLineOffset, newLines, progress }` — ONLY newly completed lines since the last emit, plus the full `DiffStreamProgress`.

### Decisive source
```ts
const stateChanged =
	lastProgress === null ||
	progress.stableCommonLines !== lastProgress.stableCommonLines ||
	progress.oldDone !== lastProgress.oldDone ||
	progress.newDone !== lastProgress.newDone ||
	progress.binary !== lastProgress.binary ||
	progress.tooLarge !== lastProgress.tooLarge;
if (oldLines.length > 0 || newLines.length > 0 || stateChanged) {
	onProgress({ oldLineOffset, oldLines, newLineOffset, newLines, progress });
}
oldLineOffset = progress.oldLines;
newLineOffset = progress.newLines;
lastProgress = progress;
```

**Flow:** Each source-side mutation calls `emit()` → pull `progress()`, slice `lines()` from the stored per-side offsets (so only NEW complete lines cross to JS) → emit when new lines exist OR any of the five state flags moved → advance offsets and remember `lastProgress`. The pane's `updateStream` splices these lines into its provisional document at exactly the given offsets.
**Invariant:** Offsets are advanced by the CONSUMER-visible counts (`progress.oldLines/newLines`), never by the sliced lengths — a flag-only emit (e.g. binary flipped) must still advance offsets so lines are not re-sent; duplicate-free delivery depends on this.
**Probe:** `grep -nF 'progress.stableCommonLines !== lastProgress.stableCommonLines' packages/coding-agent/src/cli/git-tui/state.ts` → line `472`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "streamContents FileStreamUpdate oldLineOffset emit stableCommonLines", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the delta-slice + flag-gate emit shape; adapt the transport (this is an in-process callback); omit the 4 ms poll variant for worktree files if your reader pushes instead. Direct test: behavioral via git-tui-stream tests; the emit math itself is exercised indirectly (coverage caveat — no dedicated unit file).
