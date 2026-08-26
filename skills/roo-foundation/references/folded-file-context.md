<!-- capsule-v2 -->
# Folded file context — how do you re-attach the SHAPE of every file read so far after condensing away their contents?

**Source:** Roo-Code Apache-2.0 `main@b867ec9145750d0ae1ff7f02d35406e9bf2a0b16`; Codebase Memory `Roo-Code`. **Question:** After a fresh-start condense deletes file bodies from context, what keeps the model oriented in those files?

## generateFoldedFileContext: tree-sitter signatures, per-file blocks, character-budgeted truncation
**Path/Symbol:** `src/core/condense/foldedFileContext.ts:76-168` (`generateFoldedFileContext`); error-string filter `isTreeSitterErrorString` :10-14; input assembly `FileContextTracker.getFilesReadByRoo` (`src/core/context-tracking/FileContextTracker.ts:218-260`, recency-sorted); injection at `src/core/condense/index.ts:410-432`.
**Signature:** `generateFoldedFileContext(filePaths: string[], { maxCharacters? = 50000, cwd, rooIgnoreController? }): Promise<FoldedFileContextResult>` with `{ content, sections[], filesProcessed, filesSkipped, characterCount }`.
**Data Shape:** One `<system-reminder>` block per file: `## File Context: <path>` + line-anchored definitions (`1--15 | export function ...`) from `parseSourceCodeDefinitionsForFile`.

### Decisive source
```ts
if (!definitions || isTreeSitterErrorString(definitions)) { result.filesSkipped++; continue }
if (currentCharCount + sectionContent.length > maxCharacters) {
  const remainingChars = maxCharacters - currentCharCount
  if (remainingChars < 200) { result.filesSkipped += filePaths.length - i; break } // stop all
  const truncated = definitions.substring(0, remainingChars - 100) + "\n... (truncated)"
  ...
}
```
Failure isolation: per-file try/catch collects failures and emits ONE batched warning (first 5 paths) instead of per-file log spam; tree-sitter's error STRINGS ("This file does not exist", "do not have permission", "Unsupported file type:") are pattern-matched and skipped rather than embedded into the prompt.

**Flow:** recency-sorted read list → per-file signature fold → budget walk that either fits, truncates-in-place (≥200 chars room), or hard-stops the rest → sections appended to the summary message as separate content blocks AFTER command blocks.
**Invariant:** The list MUST arrive most-recent-first (getFilesByRoo guarantees it) because the budget starves the tail — porters feeding arbitrary-order lists silently lose the oldest files' structure. Folded context is best-effort: any failure shrinks the summary, never fails the condense.
**Probe:** `src/core/condense/__tests__/foldedFileContext.spec.ts` (`generateFoldedFileContext` :34+, summarize-integration :214+).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Roo-Code", query: "generateFoldedFileContext parseSourceCodeDefinitionsForFile system-reminder", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt signatures-only folding with strict char budgeting over a recency-sorted read ledger. Adapt the tree-sitter service call to your parser. Omit the `<system-reminder>` wrapper text if your model already treats such blocks as system-trusted.
