<!-- capsule-v2 -->
# Structured edit diff — pre-mutation snapshots + unique-line inference → ACP diff content

**Source:** pi-acp-jetbrain MIT `main@27aac05f`; Codebase Memory `pi-acp`. **Question:** How does the adapter emit a structured ACP `diff` (oldText/newText) for pi's edit/write tools, including a best-effort 1-based line number?

## Structured edit diff
**Path/Symbol:** `src/acp/session.ts` — `fileSnapshots` (326), `findUniqueLineNumber` (66-80), `getToolPath` (82-87), `getParsedEdits`/`getEditOldTexts` (92-144), `toToolCallLocations` (146-152), `tool_execution_start` snapshot capture (724-747), `tool_execution_end` diff emission (818-856).
**Signature:** `findUniqueLineNumber(text: string, needle: string): number | undefined`; `toToolCallLocations(args, cwd, line?): ToolCallLocation[] | undefined`.
**Data Shape:** `fileSnapshots: Map<toolCallId, { path, oldText: string|null }>`; `fileMutationToolCallIds: Set<toolCallId>`. Edit args match pi's schema `{ path, edits: [{oldText,newText}] }` with legacy top-level `oldText`/`newText` and stringified `edits` accepted.

### Decisive source
```ts
// findUniqueLineNumber: only emit a line if the needle occurs EXACTLY once
const first = text.indexOf(needle)
if (first < 0) return undefined
const second = text.indexOf(needle, first + needle.length)
if (second >= 0) return undefined   // ambiguous -> no line
// count newlines before `first`, +1
```
```ts
// tool_execution_start: snapshot BEFORE the mutation
if (isFileMutation) {   // toolName === 'edit' || 'write'
  this.fileMutationToolCallIds.add(toolCallId)
  const p = getToolPath(args)
  if (p) {
    try {
      const abs = isAbsolute(p) ? p : resolvePath(this.cwd, p)
      snapshotOldText = readFileSync(abs, 'utf8')
      this.fileSnapshots.set(toolCallId, { path: p, oldText: snapshotOldText })
      if (toolName === 'edit')
        for (const needle of getEditOldTexts(args)) { line = findUniqueLineNumber(snapshotOldText, needle); if (typeof line === 'number') break }
    } catch { this.fileSnapshots.set(toolCallId, { path: p, oldText: null }) }
  }
}
```
```ts
// tool_execution_end: emit diff only if the file actually changed
const snapshot = this.fileSnapshots.get(toolCallId)
if (!isError && snapshot) {
  const newText = readFileSync(abs, 'utf8')
  if (snapshot.oldText === null || newText !== snapshot.oldText) {
    hasStructuredDiff = true
    content = [{ type: 'diff', path: snapshot.path, oldText: snapshot.oldText, newText }]
  }
}
```

**Flow:** At `tool_execution_start` for edit/write, read the file before the mutation into `fileSnapshots`; for edit, infer a 1-based line from the unique `oldText` needle (only if it occurs exactly once). At `tool_execution_end`, re-read the file; if it changed (or the snapshot was null), emit `content: [{type:'diff', path, oldText, newText}]`; otherwise fall back to text content. `toToolCallLocations` resolves relative paths against the session cwd.

**Invariant:** The file is snapshotted BEFORE the tool runs (so the diff is the realized change, not the requested args); a line number is emitted only when the `oldText` needle is unique (ambiguous matches yield no line); the diff is emitted only when the file actually changed.

**Probe:** `test/component/session-diff.test.ts` ("PiAcpSession: emits ACP diff content for edit tool from actual before/after file contents", "PiAcpSession: edit diff uses realized fuzzy-match file contents instead of requested args", "PiAcpSession: emits write diff content for new files on completion") and `test/component/session-events.test.ts` ("PiAcpSession: emits edit tool line when oldText matches uniquely", "PiAcpSession: omits edit tool line when oldText matches multiple times").

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-acp", query: "findUniqueLineNumber fileSnapshots getParsedEdits", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the pre-mutation snapshot, unique-line inference, and change-gated structured diff emission. Adapt the edit-args schema parsing and the path resolution to the target agent. Omit the fuzzy-match/realized-file nuance unless the target agent applies fuzzy edits.
