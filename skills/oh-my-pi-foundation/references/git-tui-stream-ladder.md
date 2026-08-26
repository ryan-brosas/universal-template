<!-- capsule-v2 -->
# Streaming side-source ladder — how does the git TUI feed old/new file contents into a DiffStream with binary/LFS/too-large classification before committing to live streaming?

**Source:** oh-my-pi (see pack SKILL.md Provenance) MIT `main@2b66ee69f2`; Codebase Memory `oh-my-pi`. **Question:** How are git-object vs worktree sides routed, when does buffered sniffing hand off to true streaming, and how do errors degrade per side?

## Sniff-then-stream ingestion
**Path/Symbol:** `packages/coding-agent/src/cli/git-tui/state.ts:` `streamContents` (:457–545), `#streamGitSide` (:547–614), `#streamFileSide` (:616–667), `#finishBufferedSide` (:669–714); emit closure :466–483.
**Signature:** `async streamContents(file: ChangedFile, onProgress: (update: FileStreamUpdate) => void, signal?): Promise<FileContents>`; internal `(stream, side, spec|path, filePath, emit, signal) => Promise<FileAssetSide>`.
**Data Shape:** `FileStreamUpdate {oldLineOffset, oldLines, newLineOffset, newLines, progress}`; result `FileContents = {kind:"text", oldText, newText, streamResult} | {kind:"asset", old, new}` where side kind ∈ empty/text/binary/image/tooLarge.

### Decisive source
```ts
for await (const chunk of git.show.stream(this.cwd, spec, { maxOutputBytes: MAX_FILE_BYTES, signal })) {
	byteLength += chunk.byteLength;
	if (streaming) {
		const progress = stream.pushBytes(side, chunk);
		emit();
		if (progress.binary) { stream.finishSide(side); emit(); return { kind: "binary" }; }
		continue;
	}
	chunks.push(chunk);
	const header = concatChunks(chunks, Math.min(byteLength, BINARY_SNIFF_BYTES));
	const keepBuffered = pathLooksLikeImage(filePath) || couldBeLfsPointer(header)
		|| looksLikeSvg(header, filePath) || isProbablyBinaryHeader(header);
	if (keepBuffered || byteLength < BINARY_SNIFF_BYTES) continue;
	streaming = true;
	for (const buffered of chunks) stream.pushBytes(side, buffered);   // replay the buffer
	chunks.length = 0;
	emit();
}
```

**Flow:** area switch routes sides — unstaged: `:0:path` git object vs disk file (untracked ⇒ old empty; deleted ⇒ new empty), staged: `HEAD:orig` vs `:0:path`, commit: first-parent blob vs head blob → both sources run CONCURRENTLY under `Promise.all` while `emit()` drains newly complete lines to the pane → non-streamed tails resolve via `#finishBufferedSide` (LFS pointer resolution → image decode → binary/text classification) → both-diffable ⇒ final `{kind:"text"}` with `await stream.finish(DIFF_CONTEXT_LINES)`; any asset side ⇒ `{kind:"asset"}`.
**Invariant:** Nothing enters the native stream until the first `BINARY_SNIFF_BYTES` prove text-safety — image/SVG/LFS/binary candidates stay fully buffered so their bytes can be reclassified without having polluted UTF-8 line state. Error ladder per side: abort rethrows; `GitOutputTruncatedError` ⇒ `markTooLarge` + `{kind:"tooLarge"}`; other `GitCommandError` ⇒ `finishSide` + `{kind:"empty"}` (a missing blob renders as an empty side, not a failed pane). The file-side poll loop (`while (!done) { await Bun.sleep(4); emit(); }` :660–663) keeps progressive rows flowing while the native read promise pends.
**Probe:** `packages/coding-agent/test/git-tui-stream.test.ts` — `"uses an empty base side for a staged added file"` pins the unstaged/staged routing; `"keeps invalid UTF-8 Git objects out of the text renderer"` pins the binary-classification arm. Byte-exact greps at pin: `BINARY_SNIFF_BYTES` header concat @state.ts:573, `Bun.sleep(4)` @:661, 3 × `markTooLarge` sites.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "streamContents streamGitSide emit", limit: 10, fields: ["signature", "name", "file"] });
```
Live-resolved @2b66ee69: `streamContents state.ts:457-545`, `#streamGitSide :547-614`.

## Verdict
Adopt sniff-buffer-then-stream whenever a byte source may turn out non-textual and your consumer needs typed degradation (binary/image/too-large/empty). Adapt the LFS/SVG arms to your host's asset support; preserve per-side error isolation so one broken side degrades alone. Omit the Bun.file specifics if your fs layer differs.
