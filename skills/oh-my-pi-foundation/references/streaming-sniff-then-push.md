<!-- capsule-v2 -->
# streaming-sniff-then-push — when does a streamed diff side switch from buffering to live pushing, and what does a sniff hit cost?

**Source:** oh-my-pi MIT `main@2b66ee69f2`; Codebase Memory `oh-my-pi`. **Question:** A porter streaming file bytes into a two-sided differ must decide per chunk: buffer for asset detection or push for live display. What is the exact gate, and what happens to a small text file?

## #streamGitSide
**Path/Symbol:** `packages/coding-agent/src/cli/git-tui/state.ts` (`GitFileModel.#streamGitSide`).
**Signature:** `async #streamGitSide(stream: DiffStream, side: DiffSide, spec: string, filePath: string, emit: () => void, signal?: AbortSignal): Promise<FileAssetSide>`.
**Data Shape:** Returns `FileAssetSide` = `{kind:"text", byteLength?} | {kind:"binary"} | {kind:"empty"} | {kind:"tooLarge"} | ...asset variants`; `MAX_FILE_BYTES = 4 * 1024 * 1024`, `BINARY_SNIFF_BYTES` from pi-utils.

### Decisive source
```ts
chunks.push(chunk);
const header = concatChunks(chunks, Math.min(byteLength, BINARY_SNIFF_BYTES));
const keepBuffered =
	pathLooksLikeImage(filePath) ||
	couldBeLfsPointer(header) ||
	looksLikeSvg(header, filePath) ||
	isProbablyBinaryHeader(header);
if (keepBuffered || byteLength < BINARY_SNIFF_BYTES) continue;

streaming = true;
for (const buffered of chunks) stream.pushBytes(side, buffered);
chunks.length = 0;
emit();
```

**Flow:** Buffer chunks until the sniff window is complete → re-check the four detectors each chunk; any positive detector means the side stays buffered and finishes as an asset (image/SVG/LFS/binary path in `#finishBufferedSide`) → otherwise flip `streaming = true` once and replay ALL buffered chunks through `pushBytes` in order, then stream every subsequent chunk directly. After EOF, a never-streamed side goes to `#finishBufferedSide`; a streamed side calls `finishSide` and returns `{kind:"text", byteLength}`.
**Invariant:** Chunks are pushed strictly in arrival order (buffered replay first); the streaming decision is made at most once per side and never revisited — a mid-stream binary reveal is handled by `progress.binary` (checked after each push), not by un-flipping.
**Probe:** `grep -nF 'keepBuffered || byteLength < BINARY_SNIFF_BYTES' packages/coding-agent/src/cli/git-tui/state.ts` → line `579`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "streamGitSide keepBuffered BINARY_SNIFF pushBytes streaming", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the sniff-window gate (small files pay zero streaming benefit but stay correct; big text files flip after one sniff window) and the ordered-replay rule; adapt the four detectors to your asset taxonomy; omit the LFS-pointer resolution chain if you have no LFS. Direct test: covered behaviorally via `git-show-byte-stream` + `diff-stream-native-diff`; no dedicated unit test for the flip itself (coverage caveat).
