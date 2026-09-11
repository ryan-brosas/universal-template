<!-- capsule-v2 -->
# apply_patch parser — what exactly does the Codex patch grammar accept, and where is it lenient?

**Source:** Roo-Code Apache-2.0 `main@b867ec9145750d0ae1ff7f02d35406e9bf2a0b16`; Codebase Memory `Roo-Code`. **Question:** Which malformations must a patch parser reject loudly, and which does this one deliberately forgive because models emit them anyway?

## Marker grammar with two deliberate leniencies
**Path/Symbol:** `src/core/tools/apply-patch/parser.ts:parsePatch` (lines 297–332) + `parseOneHunk` :201 + `parseUpdateFileChunk` :107; error type `ParseError` :31 (message prefixed `Line N:`).
**Signature:** `function parsePatch(patch: string): ApplyPatchArgs` where `ApplyPatchArgs = { hunks: Hunk[]; patch: string }`; `Hunk = AddFile{path,contents} | DeleteFile{path} | UpdateFile{path,movePath,chunks}`; `UpdateFileChunk = { changeContext: string|null, oldLines: string[], newLines: string[], isEndOfFile: boolean }`.
**Data Shape:** markers are exact constants — `*** Begin Patch`, `*** End Patch`, `*** Add File: `, `*** Delete File: `, `*** Update File: `, `*** Move to: `, `*** End of File`, `@@ `/`@@`. Hunk lines are single-char-prefixed (` ` context → both sides, `+` added → newLines only, `-` removed → oldLines only).

### Decisive source
```ts
// Lenient mode 1: heredoc wrapper
if ((firstLine === "<<EOF" || firstLine === "<<'EOF'" || firstLine === '<<"EOF"') &&
    lastLine?.endsWith("EOF")) { effectiveLines = lines.slice(1, lines.length - 1) }
// Lenient mode 2: first chunk of an update hunk may skip the @@ marker
const { chunk, linesConsumed } = parseUpdateFileChunk(
    remainingLines, lineNumber + parsedLines,
    chunks.length === 0, // Allow missing context for first chunk
)
```

**Flow:** trim → `\n` split → optional heredoc unwrap → boundaries checked (first line MUST be Begin marker, last MUST be End marker after trim) → loop `parseOneHunk` until consumed. Inside an update chunk: bare `@@` sets changeContext null, `@@ text` sets it to the remainder; a line that starts with none of ` +-` ENDS the chunk silently if ≥1 line was parsed (implicit next-hunk boundary) but throws ParseError if it's the first line; empty string inside a hunk is CONTEXT on both sides; `*** End of File` sets `isEndOfFile` and stops. Between chunks blank lines are skipped and any `***…` line ends the file op.
**Invariant:** the ONLY two leniencies are (a) shell-heredoc wrapper unwrap (`<<'EOF'` … trailing-anything-EOF), everything else is strict; and (b) missing `@@` allowed for the FIRST chunk only (`allowMissingContext = chunks.length === 0`) — later chunks REQUIRE the context marker. An empty update-file hunk throws ("is empty"); a heredoc needs ≥4 lines before the wrap check even runs.
**Probe:** `grep -c '"<<EOF"' src/core/tools/apply-patch/parser.ts` → 1 (heredoc ladder); `grep -c 'chunks.length === 0' src/core/tools/apply-patch/parser.ts` → 2 (leniency flag + empty-hunk guard); `grep -cF 'EOF_MARKER' src/core/tools/apply-patch/parser.ts` → 2.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Roo-Code", query: "parsePatch heredoc EOF ParseError", limit: 10 });
```
(live-verified rank#1 parsePatch :297–332).

## Verdict
Adopt the exact marker grammar, both leniencies, and the first-chunk-only rule — porting strict-everywhere breaks real model output, porting lenient-everywhere hides malformed patches. Adapt error message wording. Omit nothing else. Coverage caveat: no direct unit spec for parser.ts at pin (the wrapper spec `applyPatchTool.partial.spec.ts` covers streaming preview only); pinned via source read + greps.
