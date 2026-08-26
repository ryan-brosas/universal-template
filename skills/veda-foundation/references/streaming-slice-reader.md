<!-- capsule-v2 -->
# Streaming slice reader — windowed line reads without loading whole files, null-byte binary gate

**Source:** Veda (`veda-ts`, MIT, `master@f050518c99fa54a5a0af4a04918aaf01d1ed94e1`); Codebase Memory `veda`. **Question:** How do I read an arbitrary line range from a possibly-huge file memory-safely while still detecting binary content?

## readline window over createReadStream, full-file fast path
**Path/Symbol:** `src/context/readSlice.ts:readSliceText` (:24–117).
**Signature:** `async function readSliceText(opts: { cwd: string; slice: FileSlice; displayPath?: string }): Promise<Result<ReadSliceResult>>`.
**Data Shape:** Success payload `{ absolutePath, displayPath, content, startLine, endLine, lineCount, sliceType }`; failure is `err(Error)` via the host's `Result` helper. `endLine` reports ACTUAL last line captured, not the requested bound.

### Decisive source
```ts
if (slice.sliceType === 'full') {
  const content = await file.text();               // fast path
  if (content.includes('\0')) return err(new Error(`Binary file skipped (contains null bytes): ${displayPath}`));
  ...
}
// Memory-efficient slicing using line iterator
const startLine = Math.max(1, slice.startLine ?? 1);
const endLine = slice.sliceType === 'single-line' ? startLine : (slice.endLine ?? Infinity);
const rl = createInterface({ input: createReadStream(absolutePath), crlfDelay: Infinity });
try {
  for await (const line of rl) {
    if (currentLine >= startLine && currentLine <= endLine) { lines.push(line); actualEndLine = currentLine; }
    if (currentLine >= endLine) { currentLine++; break; }
    currentLine++;
  }
} finally { rl.close(); }
// If startLine was beyond the end of the file
if (currentLine < startLine) return ok({ ..., content: '', startLine, endLine: startLine, lineCount: 0, ... });
```

**Flow:** exists-check → displayPath = cwd-relative unless it escapes upward (`..`) → full slices take `Bun.file().text()` fast path → sliced reads stream line-by-line, collecting only the window → break as soon as the window closes → past-EOF start yields an EMPTY OK result (not an error). Null-byte scan gates BOTH paths.
**Invariant:** Binary detection is a `\0` membership check applied to exactly the extracted bytes (sliced reads never scan the whole file); a short read is reported honestly via `actualEndLine || startLine` rather than padded to the requested window. `rl.close()` sits in `finally` so early breaks never leak the stream.
**Probe:** `tests/context/store-performance.test.ts` covers store-scale behavior; the slicing loop's observable boundary (empty result for out-of-range start, actualEndLine truth) is pinned by the mirror logic exercised through `tests/context/slice.test.ts` extract tests on the pure twin `extractSlice`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pi-ecosystem-veda", query: "readSliceText createInterface crlfDelay", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the streaming-window pattern (readline over createReadStream, break-on-window-close, finally-close) and the empty-ok past-EOF contract. Adapt `Bun.file` to your runtime's equivalent fast-path reader. Omit the Result wrapper if your host has its own error channel — but keep failures as errors, not sentinel strings.
