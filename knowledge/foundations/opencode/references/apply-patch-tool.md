<!-- capsule-v2 -->
# Apply-patch tool — parse, verify, and apply hunks

**Source:** opencode MIT `<branch>@<commit>`; Codebase Memory `opencode`. **Question:** how does a unified-diff patch get parsed, verified, and applied without corrupting files?

## Connected graph-selected seam
**Path/Symbol:** `packages/opencode/src/tool/apply_patch.ts` (313 lines): `Parameters` (:18), `ApplyPatchTool` (:22), `execute` (:38-130+); `packages/opencode/src/patch/index.ts`: `parsePatch` (:185), `deriveNewContentsFromChunks` (:307), `applyHunksToFiles` (:514).
**Signature:** `execute({patchText}, ctx)` — `Patch.parsePatch(params.patchText)` → hunks; each hunk resolved by `path.resolve(instance.directory, hunk.path)`, applied by type (create/update/delete); `deriveNewContentsFromChunks` computes new content.
**Data Shape:** `Parameters = {patchText: string}`; hunks have `{path, type, contents?, chunks?}`; zero hunks → `Effect.fail("apply_patch verification failed: no hunks found")`.

### Decisive source
```ts
const parseResult = Patch.parsePatch(params.patchText)
hunks = parseResult.hunks
if (hunks.length === 0) {
  return yield* Effect.fail(new Error("apply_patch verification failed: no hunks found"))
}
for (const hunk of hunks) {
  const filePath = path.resolve(instance.directory, hunk.path)
  switch (hunk.type) {
    case "create": /* contents, ensure trailing newline */
    case "update": /* Patch.deriveNewContentsFromChunks(filePath, hunk.chunks, ...) */
    case "delete": /* remove file */
  }
}
```

**Flow:** parse the unified-diff text into hunks → fail loudly if zero → for each hunk, resolve the path and apply by type (create ensures trailing newline; update derives new content from chunks; delete removes). Verification happens before any mutation.
**Invariant:** a patch with no hunks fails (never silently no-ops); create ensures a trailing newline; update recomputes content from chunks (not blind text replace).
**Probe:** `packages/opencode/test/tool/apply_patch.test.ts` (create/update/delete hunks; zero-hunk failure; trailing-newline on create; content derived correctly on update).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "opencode", query: "ApplyPatchTool parsePatch hunks create update delete deriveNewContents", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the parse-verify-apply patch flow with zero-hunk failure and trailing-newline guarantee; adapt the patch dialect to host; omit the Effect service wiring unless the target uses Effect.
