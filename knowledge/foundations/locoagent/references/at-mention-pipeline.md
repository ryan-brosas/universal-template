<!-- capsule-v2 -->
# At-mention file pipeline — from @token to typed attachment: quoting, line ranges, directories, PDFs, and dedup?

**Source:** locoagent (Claude Code CLI fork, rev `c01bb3f`); Codebase Memory `locoagent`. **Question:** the full extraction-and-attachment ladder for user-typed @-mentions.

## extract / parse / process / generate
**Path/Symbol:** `extractAtMentionedFiles` (:2757-2790), `parseAtMentionedFileLines` (:2836-2852), `processAtMentionedFiles` (:1894-1964), `tryGetPDFReference` (:2986-3018), `generateFileAttachment` (:3020-3199).
**Signature:** extract `(content) → string[]` (quoted-first, then bare, uniq'd); parse `(mention) → { filename, lineStart?, lineEnd? }` via `/^([^#]+)(?:#L(\d+)(?:-(\d+))?)?(?:#[^#]*)?$/`; generate returns one of File | CompactFileReference | PDFReference | AlreadyRead | null.
**Data Shape:** mention syntax: `@file.txt`, `@"my file.txt"`, `@file.txt#L10-20`; MCP resources use `@server:uri` with URI colons REJOINED (`mention.split(':')` then `uriParts.join(':')` :2007-2008).

### Decisive source
```ts
if (existingFileState && mode === 'at-mention') {
  const mtimeMs = await getFileModificationTimeAsync(filename)
  // Handle timestamp format inconsistency:
  // - FileReadTool stores Date.now() (current time when read)
  // - FileEdit/WriteTools store mtimeMs (file modification time)
  // If timestamp > mtimeMs, it was stored by FileReadTool using Date.now()
  // ...Only use optimization when timestamp <= mtimeMs,
  // indicating it was stored by FileEdit/WriteTool with actual mtimeMs.
  if (existingFileState.timestamp <= mtimeMs &&
      mtimeMs === existingFileState.timestamp)
    return { type: 'already_read_file', /* cached content, no API bytes */ }
}
```
plus the truncation ladder: catch `MaxFileReadTokenExceededError | FileTooLargeError` → `readTruncatedFile()` → compact-mode returns bare `compact_file_reference`; at-mention mode reads only first MAX_LINES_TO_READ lines with `truncated: true`.

**Flow:** deny-rule check FIRST (watchers and mentions both respect read denies) → size-limit check (PDFs exempted — they have their own page-based handling) → PDF branch: page count via pdfinfo else ~100KB/page heuristic; > threshold → lightweight reference attachment instead of inlining → already-read short-circuit (timestamp-consistency guarded) → validateInput → full read → token/size errors degrade to truncated read → all failures return null (never throw). Directory mentions render a readdir listing capped at 1000 entries with an "… and N more" tail line.
**Invariant:** extraction must handle quoted spaces BEFORE bare tokens (bare regex would truncate at whitespace); the timestamp-format mismatch between tools means naive equality checks against Date.now()-stamped entries silently disable the optimization — the guard keeps it correct-by-skepticism; oversized files DEGRADE (truncate/reference) rather than fail.
**Probe:** no upstream test (coverage caveat). Deterministic probe: regexes pinned verbatim :2764-2765/:2841; timestamp comment :3083-3090.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "extractAtMentionedFiles generateFileAttachment already_read_file PDF reference", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt the quoted/bare dual-regex extraction, line-range suffix parse, and degrade-not-fail read ladder; adapt thresholds; omit PDF heuristics if your host has no docs flow. Porting trap: comparing cache timestamps across tools' differing conventions either always-misses or falsely claims freshness; forgetting to rejoin URI colons drops every resource whose URI contains `://`.
