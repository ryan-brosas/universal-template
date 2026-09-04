<!-- capsule-v2 -->
# apply-patch replacement engine — in what order do hunks mutate the file, and how are pure additions anchored?

**Source:** Roo-Code Apache-2.0 `main@b867ec9145750d0ae1ff7f02d35406e9bf2a0b16`; Codebase Memory `Roo-Code`. **Question:** How does the applier turn parsed chunks into a new file without index corruption, and where do context-free additions land?

## Compute-then-apply-in-reverse
**Path/Symbol:** `src/core/tools/apply-patch/apply.ts:computeReplacements` (lines 38–95), `applyReplacements` :101, `applyChunksToContent` :123.
**Signature:** `computeReplacements(originalLines: string[], filePath: string, chunks: UpdateFileChunk[]): Array<[number, number, string[]]>`; `applyChunksToContent(originalContent: string, filePath: string, chunks: UpdateFileChunk[]): string`.
**Data Shape:** replacement tuple = `[startIndex, oldLength, newLines]`. Input lines have the trailing empty element (from final `\n`) DROPPED before matching; output always re-appends a trailing empty element so the file ends with `\n`.

### Decisive source
```ts
if (chunk.oldLines.length === 0) {
    // Pure addition (no old lines). Add at the end or before final empty line.
    const insertionIdx =
        originalLines.length > 0 && originalLines[originalLines.length - 1] === ""
            ? originalLines.length - 1
            : originalLines.length
    replacements.push([insertionIdx, 0, chunk.newLines])
    continue
}
…
// Apply in reverse order so earlier replacements don't shift later indices
for (let i = replacements.length - 1; i >= 0; i--) {
    const [startIdx, oldLen, newSegment] = replacements[i]!
    result.splice(startIdx, oldLen, ...newSegment)
}
```

**Flow:** per chunk — if `changeContext` is set, seek it from the running cursor and advance past it (`lineIndex = idx + 1`, failure throws `Failed to find context '<ctx>' in <path>`); pure addition anchors at end-of-file (before a trailing blank line if one exists); otherwise `seekSequence` for oldLines at the cursor, ONE retry after stripping a single trailing empty string from pattern AND replacement (trailing-newline tolerance); success records `[found, pattern.length, newSlice]` and advances the cursor past the match. All replacements are then sorted by start index and spliced in REVERSE order. Total failure carries a 200-char preview of expected lines.
**Invariant:** chunks are positional — each must match AT OR AFTER the previous match's end (the monotonic `lineIndex` cursor); a patch whose second hunk targets text before its first will fail even though both patterns exist in the file. Reverse-order application is what keeps computed indices valid; applying forward corrupts every subsequent splice. The trailing-empty-line retry strips from BOTH pattern and replacement together or not at all.
**Probe:** `grep -c 'originalLines\[originalLines.length - 1\] === ""' src/core/tools/apply-patch/apply.ts` → 2 (drop-trailing + pure-addition anchor); `grep -c 'replacements.sort' src/core/tools/apply-patch/apply.ts` → 1.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Roo-Code", query: "computeReplacements applyChunksToContent replacements reverse", limit: 10 });
```
(live-verified rank#1 computeReplacements :38–95).

## Verdict
Adopt compute-then-reverse-splice, the positional cursor, and the before-trailing-blank pure-addition anchor. Adapt the error-preview length. Omit nothing. Coverage caveat: no direct spec for apply.ts at pin; pinned via source read + greps (consumers' approval flow covered by tool-level specs).
