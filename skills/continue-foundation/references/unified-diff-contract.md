<!-- capsule-v2 -->
# Unified diff contract — how are before/after states normalized, displayed, and parsed back into structured hunks?

**Source:** Continue (Apache-2.0) `main@5522c6f44ca0ac3528b37244818fbfa39b5af470`; Codebase Memory `continue`. **Question:** What must a porter know about trailing-newline normalization, path display fallbacks, and the header-strip convention before generating or consuming these diffs?

## Three formats, one normalization rule
**Path/Symbol:** `core/nextEdit/context/diffFormatting.ts:createDiff` (:25-46), `createUnifiedDiff` (:48-81), `createBeforeAfterDiff` (:83-102), `extractMetadataFromUnifiedDiff` (:138-247).
**Signature:** `createDiff({beforeContent, afterContent, filePath, diffType, contextLines, workspaceDir?}): string`; `extractMetadataFromUnifiedDiff(unifiedDiff: string): DiffMetadata`.
**Data Shape:** `DiffFormatType ∈ {Unified: "unified", RawBeforeAfter: "beforeAfter", TokenLineDiff: "linediff"}`; `DiffMetadata = {oldFilename?, newFilename?, oldTimestamp?, newTimestamp?, hunks[], isBinary?, isNew?, isDeleted?, isRename?}`.

### Decisive source
```ts
const normalizedBefore = beforeContent.endsWith("\n") ? beforeContent : beforeContent + "\n";
const normalizedAfter  = afterContent.endsWith("\n")  ? afterContent  : afterContent + "\n";

let displayPath = filePath;
if (workspaceDir && filePath.startsWith(workspaceDir)) {
  displayPath = filePath.slice(workspaceDir.length).replace(/^[\\/]/, "");   // relative to workspace
} else if (workspaceDir) {
  displayPath = getUriPathBasename(filePath);                                 // fallback: basename only
}
const patch = createPatch(displayPath, normalizedBefore, normalizedAfter, undefined, undefined, { context: contextLines });
```
```ts
// parser: header lines carry optional timestamps after TAB
const oldFileMatch = lines[0].match(/^--- (a\/)?(.+?)(?:\t(.+))?$/);
if (metadata.oldFilename === "/dev/null") metadata.isNew = true;
const hunkHeaderRegex = /^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@(?:\s(.*))?$/;   // count defaults to 1 when omitted
if (line.includes("Binary files") || line.includes("GIT binary patch")) metadata.isBinary = true;
```

**Flow:** normalize BOTH contents to end with `\n` → choose display path (relative > basename) → jsdiff `createPatch` with `{context}` hunk context. The reverse direction parses `---/+++` headers (`a/`, `b/` prefixes stripped; tab-separated timestamps captured), walks `@@` hunks assigning old/new line numbers per ` `/`+`/`-` line, and flags new/deleted files via `/dev/null`.
**Invariant:** Every producer appends the missing trailing newline BEFORE diffing — without it the last-line edit renders as `\ No newline at end of file` noise and downstream parsers mis-assign line numbers. Consumers strip the FIRST FOUR LINES of a stored unidiff to drop its header (`unidiff.split("\n").slice(4)` in processNextEditData) — so any change to `createPatch`'s header shape breaks that convention. `TokenLineDiff` is an UNIMPLEMENTED slot returning `""` (TODO in source) and `RawBeforeAfter` falls through the switch — `createDiff` returns `""` for both, by design.
**Probe:** `core/nextEdit/context/diffFormatting.vitest.ts` — suites at :17 createDiff / :198 createBeforeAfterDiff / :253 extractMetadataFromUnifiedDiff (528L of direct tests incl. rename/binary/new-file cases).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "continue", query: "createDiff extractMetadataFromUnifiedDiff createPatch", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt trailing-newline normalization, the two-step display-path fallback, and the 4-line header-strip consumption convention; adapt format enum to your needs but keep `createPatch({context})` semantics for parseability; omit TokenLineDiff (dead slot). Direct vitest suite exists — green at this pin.
