<!-- capsule-v2 -->
# Write tool — permission-gated full-file write with BOM/format/LSP feedback

**Source:** opencode MIT `<branch>@<commit>`; Codebase Memory `opencode`. **Question:** how does a full-file write stay safe (permission-gated, encoding-preserving, LSP-checked)?

## Connected graph-selected seam
**Path/Symbol:** `packages/opencode/src/tool/write.ts` (104 lines): `Parameters` (:47-57), `WriteTool` (:58), `execute` (:66-103).
**Signature:** `execute({content, filePath}, ctx)` — resolves absolute path (joins `instance.directory` for relative), `assertExternalDirectoryEffect`, reads existing source (BOM-aware), asks permission with a diff, writes, formats, publishes events, touches LSP, reports diagnostics.
**Data Shape:** `Parameters = {content: string, filePath: string}` (absolute path required); output = "Wrote file successfully." + LSP error blocks (own file + up to 5 project files).

### Decisive source
```ts
const exists = yield* fs.existsSafe(filepath)
const source = exists ? yield* Bom.readFile(fs, filepath) : { bom: false, text: "" }
const next = Bom.split(params.content)
const desiredBom = source.bom || next.bom
const diff = trimDiff(createTwoFilesPatch(filepath, filepath, contentOld, contentNew))
yield* ctx.ask({ permission: "edit", patterns: [path.relative(instance.worktree, filepath)], ... })
yield* fs.writeWithDirs(filepath, Bom.join(contentNew, desiredBom))
```

**Flow:** resolve absolute path → external-directory guard → read existing (BOM-aware) → compute diff → `ctx.ask` permission gate (with the diff in metadata) → `writeWithDirs` (creates parent dirs) → format + BOM re-sync → publish `FileSystem.Edited` + `Watcher.Updated` (add/change) → LSP touch + diagnostics report.
**Invariant:** BOM preserved (`desiredBom = source.bom || next.bom`); write is permission-gated BEFORE any mutation; LSP diagnostics feed back into the model output; `Effect.orDie` turns domain errors into defects.
**Probe:** `packages/opencode/test/tool/write.test.ts` (writes file with dirs creation; BOM preserved; permission gate invoked with the diff; LSP diagnostics appended on error).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "opencode", query: "WriteTool write permission diff BOM LSP diagnostics", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the permission-gated full-file write with BOM preservation, parent-dir creation, format re-sync, and LSP feedback; adapt the permission model and LSP integration to host; omit the Effect service wiring unless the target uses Effect.
