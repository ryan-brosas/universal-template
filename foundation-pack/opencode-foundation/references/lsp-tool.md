<!-- capsule-v2 -->
# LSP tool — language-server diagnostics feedback

**Source:** opencode MIT `<branch>@<commit>`; Codebase Memory `opencode`. **Question:** how does a coding agent surface language-server diagnostics back to the model so it fixes errors?

## Connected graph-selected seam
**Path/Symbol:** `packages/opencode/src/tool/lsp.ts` (113 lines): `Parameters` (:23), `LspTool` (:37); `packages/opencode/src/lsp/lsp.ts`: `LSP.Diagnostic.report`.
**Signature:** `execute({...}, ctx)` — returns LSP diagnostics for a file (own-file + up to `MAX_PROJECT_DIAGNOSTICS_FILES` project files).
**Data Shape:** `Parameters` (file selection); output = "LSP errors detected in this file, please fix:\n{block}" + "LSP errors detected in other files:\n{block}".

### Decisive source
```ts
// from write.ts — the LSP feedback loop
yield* lsp.touchFile(filepath, "document")
const diagnostics = yield* lsp.diagnostics()
for (const [file, issues] of Object.entries(diagnostics)) {
  const block = LSP.Diagnostic.report(current ? filepath : file, issues)
  output += `\n\nLSP errors detected in this file, please fix:\n${block}`
}
```

**Flow:** after a mutation (write/edit), the tool touches the file and reads diagnostics; it reports own-file errors first, then up to 5 project files; the model receives the error blocks as instructions to fix.
**Invariant:** diagnostics feed back into the model output (turning errors into self-correction prompts); project diagnostics are bounded (5 files).
**Probe:** `packages/opencode/test/tool/lsp.test.ts` (diagnostics reported for the touched file; project-file diagnostics bounded; report format).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "opencode", query: "LspTool LSP diagnostics report touchFile errors", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the LSP-diagnostics feedback loop (touch → read → report into model output, own-file first then bounded project files); adapt the LSP client and report format to host.
