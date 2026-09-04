<!-- capsule-v2 -->
# Truncate tool — bounded tool output with spill-to-file

**Source:** opencode MIT `<branch>@<commit>`; Codebase Memory `opencode`. **Question:** how does tool output stay within token/memory bounds and spill overflow to a file?

## Connected graph-selected seam
**Path/Symbol:** `packages/opencode/src/tool/truncate.ts` (156 lines): `MAX_LINES = 2000` (:14), `MAX_BYTES = 50*1024` (:15), `DIR`/`GLOB` (:16-17), `Result` (:19), `limits` (:43), `truncate` (:87-94).
**Signature:** `truncate(text, options?)` — if `lines.length <= maxLines && totalBytes <= maxBytes`, returns `{content: text, truncated: false}`; else spills to a file and returns `{content, truncated: true, outputPath}`.
**Data Shape:** `Result = {content, truncated: false} | {content, truncated: true, outputPath}`; limits configurable (`tool_output.max_lines` / `max_bytes`, defaulting to `MAX_LINES`/`MAX_BYTES`).

### Decisive source
```ts
const maxLines = options.maxLines ?? resolved.maxLines
const maxBytes = options.maxBytes ?? resolved.maxBytes
if (lines.length <= maxLines && totalBytes <= maxBytes) {
  return { content: text, truncated: false }
}
// else: spill to TRUNCATION_DIR and return {content, truncated: true, outputPath}
```

**Flow:** resolve limits (config override or defaults) → count lines and bytes → if within bounds, return inline; if over, spill the overflow to a file in `TRUNCATION_DIR` and return a pointer so the model can read it.
**Invariant:** output is bounded by line count AND byte count; overflow spills to a file (never dropped); the spill path is returned so the model can page it.
**Probe:** `packages/opencode/test/tool/truncation.test.ts` (within-bounds returns inline; over-lines spills to file with outputPath; over-bytes spills; config override respected).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "opencode", query: "Truncate truncate maxLines maxBytes spill outputPath", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the line+byte-bounded truncation with spill-to-file and returned outputPath; adapt the limits and spill dir to host; omit the Effect service wiring unless the target uses Effect.
