<!-- capsule-v2 -->
# Progressive diff pane + async highlight — how does the TUI paint streaming file contents and syntax-highlight large diffs without ever blocking input?

**Source:** oh-my-pi (see pack SKILL.md Provenance) MIT `main@2b66ee69f2`; Codebase Memory `oh-my-pi`. **Question:** What is the merge contract for stream updates, and what makes `highlightAsync` cancellable, incremental, and non-blocking?

## Streaming state + cooperative highlighting
**Path/Symbol:** `packages/coding-agent/src/cli/git-tui/diff-pane.ts:` `startStream` (:629–632), `updateStream` (:635–652), `highlightAsync` (:655–693), `#highlightChunk` (:695–709), `HIGHLIGHT_BATCH_LINES = 32` (:87); render twin `#renderStreaming` (:1178–1223); `createHighlightStream` from theme.
**Signature:** `updateStream(update: FileStreamUpdate): void; async highlightAsync(signal: AbortSignal, requestRender: () => void): Promise<void>`.
**Data Shape:** Pane streaming buffer `{filePath, oldLines[], newLines[], stableCommonLines, maxLineWidth}`; highlights `{old: (string|undefined)[], new: (string|undefined)[]}` indexed per display line.

### Decisive source
```ts
streaming.oldLines.splice(update.oldLineOffset,
	streaming.oldLines.length - update.oldLineOffset, ...update.oldLines);
...
while (oldOffset < doc.oldDisplayLines.length || newOffset < doc.newDisplayLines.length) {
	if (signal.aborted || this.#doc !== doc) return;      // cancel = abort OR document swap
	... oldOffset = this.#highlightChunk(oldStream, doc.oldDisplayLines, doc.oldEndsNewline, highlights.old, oldOffset);
	requestRender();
	if (more) await Bun.sleep(0);                          // yield to the event loop between 32-line chunks
}
// #highlightChunk — feed the native HighlightStream incrementally, final chunk without trailing \n:
const chunk = `${lines.slice(offset, end).join("\n")}${!final || endsNewline ? "\n" : ""}`;
const rendered = stream.push(chunk).split("\n");
if (chunk.endsWith("\n")) rendered.pop();
```

**Flow:** pane starts provisional (`setDocument(null,"streaming")`) → each FileStreamUpdate splices new complete lines at the reported offset (offsets are absolute; arrays shrink to offset then extend — tolerant of re-emitted tails) → on final text document, `highlightAsync` walks both sides in 32-line batches through the native incremental highlighter, repainting after every batch. Fallback: sides without a language highlighter start at full length so they render plain immediately. Lookup keeps a plain fallback per line (`highlights?.new[i] ?? lines[i]`).
**Invariant:** Cancellation is TWO-condition: the AbortSignal AND `this.#doc !== doc` (a newer document invalidates in-flight highlighting even without an abort). The trailing-newline rule is load-bearing: every non-final chunk MUST end `\n` or the tokenizer mis-lexes across the boundary; the final chunk omits it when the file lacks a trailing newline. Highlights are keyed by DISPLAY line index and rebuilt wholesale on `setDocument` (`#highlights = null`, `#docVersion++`). `stableCommonLines` is carried for renderers that pin the unchanging prefix.
**Probe:** `packages/coding-agent/test/git-tui-stream.test.ts` — `"streamed formatting document matches the synchronous builder"` pins streamed ≡ synchronous documents; `"demotes line splits that only move whitespace"` pins the formatting-mode row kinds this pane renders.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "updateStream highlightAsync streaming diff pane", limit: 10, fields: ["signature", "name", "file"] });
```
Live-resolved @2b66ee69: `DiffPane.updateStream diff-pane.ts:635-652`, `highlightAsync :655-693`.

## Verdict
Adopt batch-and-yield highlighting (32-line chunks + macrotask yields) for any large-document decoration over a native/incremental tokenizer; keep the dual cancellation latch. Adapt batch size to your frame budget; preserve trailing-newline chunk semantics exactly. Omit the tab-expansion retention if your renderer measures differently.
