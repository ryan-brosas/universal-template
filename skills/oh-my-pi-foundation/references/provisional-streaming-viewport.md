<!-- capsule-v2 -->
# provisional-streaming-viewport — what may a provisional diff viewport render before the exact diff exists, and how does it hand off?

**Source:** oh-my-pi MIT `main@2b66ee69f2`; Codebase Memory `oh-my-pi`. **Question:** While the native differ is ingesting, what document does the pane render, and what happens when the real document lands?

## DiffPane streaming state
**Path/Symbol:** `packages/coding-agent/src/cli/git-tui/diff-pane.ts` (`DiffPane.startStream`, `updateStream`, `#renderStreaming`, `StreamingDocument`).
**Signature:** `startStream(filePath: string): void`; `updateStream(update: FileStreamUpdate): void`; `#renderStreaming(width: number, height: number): string[]`.
**Data Shape:** `StreamingDocument { filePath, oldLines[], newLines[], stableCommonLines, maxLineWidth }`; pane states `"empty" | "loading" | "streaming" | "asset" | "ready"`.

### Decisive source
```ts
streaming.oldLines.splice(
	update.oldLineOffset,
	streaming.oldLines.length - update.oldLineOffset,
	...update.oldLines,
);
```

**Flow:** `setSelectFile` calls `pane.startStream(file.path)` BEFORE `streamContents` starts, so the pane shows a provisional view immediately; each `FileStreamUpdate` splices new lines at their offsets (splice length = remaining length ⇒ pure append under correct offsets); zero total lines renders a centered "Streaming file…" placeholder; rows render as line-numbered split/file view over the PROVISIONAL lines with cursor highlight — no +/- coloring, since alignment is not yet known. When `streamContents` resolves, `#rebuildDocument` calls `setDocument(buildDiffDocument(...), "ready")` which resets `#streaming = null`, scroll, and cursor.
**Invariant:** The provisional view never guesses alignment (no hunk buttons, no change colors) and every rendered row comes from `stableCommonLines`-gated complete lines; the final document REPLACES it in one frame, so stale provisional rows can never persist.
**Probe:** `grep -nF '#renderStreaming(width: number' packages/coding-agent/src/cli/git-tui/diff-pane.ts` → line `1178` and `grep -nF 'Streaming file…' packages/coding-agent/src/cli/git-tui/diff-pane.ts` → line `1184`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "startStream updateStream StreamingDocument renderStreaming provisional", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-phase contract (provisional complete-lines view → one-frame replace); adapt layout/gutters; omit the cursor-band styling. Direct test: behavioral assertions in `packages/coding-agent/test/git-tui-stream.test.ts`.
