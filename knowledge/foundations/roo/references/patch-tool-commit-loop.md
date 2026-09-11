<!-- capsule-v2 -->
# ApplyPatchTool commit loop — is a multi-file patch atomic, and what gates run before each file hits disk?

**Source:** Roo-Code Apache-2.0 `main@b867ec9145750d0ae1ff7f02d35406e9bf2a0b16`; Codebase Memory `Roo-Code`. **Question:** If a patch touches three files and the user rejects the second diff, what state is the workspace left in?

## Compute-all-then-commit-one-by-one (NOT atomic)
**Path/Symbol:** `src/core/tools/ApplyPatchTool.ts:execute` (lines 55–139) + `handleAddFile` :141 / `handleDeleteFile` :233 / `handleUpdateFile` :290 + `handlePartial` :453.
**Signature:** `execute(params: { patch: string }, task: Task, callbacks: ToolCallbacks): Promise<void>`; streaming preview via `handlePartial(task, block)`.
**Data Shape:** per-change record `{ type: "add"|"delete"|"update", path, movePath?, originalContent?, newContent? }`; approval payload = JSON `{tool:"appliedDiff", path, diff, content, isProtected, diffStats, originalContent?}` (`originalContent` only on update).

### Decisive source
```ts
// Phase 1: everything computed in memory — one failure aborts BEFORE any disk write
changes = await processAllHunks(parsedPatch.hunks, readFile)
…
// Phase 2: per-file commit loop — access checks live HERE, not in phase 1
for (const change of changes) {
    const accessAllowed = task.rooIgnoreController?.validateAccess(relPath)
    if (!accessAllowed) { … pushToolResult(formatResponse.rooIgnoreError(relPath)); return }
```

**Flow:** missing param → mistake-count++ + missing-param error; parse failure → toolError (mistake-count++); zero hunks → plain "No file operations found in patch."; phase 1 processes ALL hunks through `processAllHunks` (read file → apply chunks → newContent) so any match failure aborts with NOTHING written; phase 2 loops changes checking rooIgnore THEN write-protection PER FILE, then add (rejects if file exists: "Use Update File instead.") / delete (rejects if missing) / update (rejects if missing; empty diff → "No changes needed"). Each file shows its own diff + askApproval; rejection reverts that diff view and returns immediately. Move-to support validates destination rooIgnore + write-protection + outside-workspace BEFORE writing the new path then best-effort unlinking the old.
**Invariant:** MULTI-FILE PATCHES ARE NOT TRANSACTIONAL: compute is all-or-nothing but COMMIT is sequential — a mid-loop rejection/rooIgnore-stop leaves earlier files of the SAME patch already saved on disk. The preventFocusDisruption experiment forks every save into `saveDirectly(path, content, …)` vs diff-view open/update/saveChanges, and rejection only calls `revertChanges()` on the non-experimental branch. `consecutiveMistakeCount = 0` and `recordToolUsage("apply_patch")` fire only after the WHOLE loop completes.
**Probe:** `grep -c 'processAllHunks' src/core/tools/ApplyPatchTool.ts` → 2 (import + call); `grep -c 'validateAccess(change.movePath)' src/core/tools/ApplyPatchTool.ts` → 1; `grep -cF 'Use Update File instead.' src/core/tools/ApplyPatchTool.ts` → 1.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Roo-Code", query: "ApplyPatchTool handlePartial extractFirstPathFromPatch", limit: 10 });
```
(live-verified rank#1 extractFirstPathFromPatch :28–53, rank#3 execute :55–139).

## Verdict
Adopt the two-phase shape (compute-all → commit-sequence) and document non-atomicity as a CONTRACT, not a bug to fix silently. Adapt the experiment fork to your host's editor surface. Omit the VS Code diffViewProvider internals. Direct tests cover only the streaming preview (`src/core/tools/__tests__/applyPatchTool.partial.spec.ts`: first-header path extraction, deterministic multi-file preview, truncated-trailing-header stability at describe "ApplyPatchTool.handlePartial" :38, its :104/:118/:133/:151/:163/:182); the commit loop itself has no spec at pin.
