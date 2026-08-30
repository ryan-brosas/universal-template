<!-- capsule-v2 -->
# ToolOutputStore — how do you keep provider-facing tool output bounded while retaining the complete output durably?

**Source:** opencode MIT `dev@03521003fafd`; Codebase Memory `opencode`. **Question:** Tool outputs can be megabytes of text plus native media. The provider channel needs a bounded preview, but the full output must survive for later retrieval, and a failed retention write must not silently ship lossy output. Where does the bound happen and what are the exact semantics?

## The bound() settlement gate
**Path/Symbol:** `packages/core/src/tool-output-store.ts` (`MAX_LINES` :13, `MAX_BYTES` :14, `RETENTION` :15, `takePrefix` :50, `takeSuffix` :62, `preview` :74, `boundedPreview` :98, `limits` :119, `write` :129, `bound` :138, `cleanup` :176, `cleanupLayer` :200, `cleanupNode` :207); config shape `packages/core/src/config/tool-output.ts` (9L); call site `packages/core/src/tool/registry.ts` `settleWith` :75.
**Signature:** `bound({sessionID, toolCallID, output: ToolOutput}) → Effect<BoundResult, StorageError>` where `BoundResult = { output: ToolOutput, outputPaths: string[] }`.
**Data Shape:** defaults `MAX_LINES = 2_000`, `MAX_BYTES = 50 * 1024`, `RETENTION = Duration.days(7)`; config override `tool_output.max_lines` / `max_bytes` (PositiveInt, optional).

### Decisive source
```ts
// tool-output-store.ts:138-175 — the gate: text-only bound, media passthrough, wx-flag spill
const contextual = input.output.content.length === 0
  ? yield* Effect.try(() => JSON.stringify(input.output.structured, null, 2) ?? String(input.output.structured), ...)
  : text.map((item) => item.text).join("")
if (lineCount(contextual) <= outputLimits.maxLines && Buffer.byteLength(contextual, "utf-8") <= outputLimits.maxBytes)
  return { output: input.output, outputPaths: [] }
const outputPath = yield* write(contextual)   // fs.writeFileString(file, content, { flag: "wx" })
const marker = `... output truncated; full content saved to ${outputPath} ...`
return {
  output: { structured: input.output.structured,
    content: [{ type: "text", text: boundedPreview(contextual, marker, maxLines, maxBytes) }, ...media] },
  outputPaths: [outputPath],
}
```

**Flow:** settleWith calls bound() on EVERY settled tool output before ToolOutput.toResultValue. Text content is joined; empty content falls back to JSON.stringify(structured). Under both limits → pass through unchanged with empty outputPaths. Over → write the COMPLETE text to `global data/tool-output/tool_<ascending-id>` with the wx flag (exclusive create — never overwrite), then replace the text channel with a head/tail preview (ceil/floor half split, marker-budgeted: the marker's own bytes/lines are subtracted first) and keep media items UNLIMITED and structured metadata intact. StorageError (encode|write) fails the settlement — a tool whose full output cannot be retained errors rather than returning a lossy preview. Retention: cleanup scans the managed dir on an hourly Schedule.spaced forked loop, removing `tool_*` files older than 7 days by mtime, ignoring unrelated files; it runs ONCE globally (makeGlobalNode), not per location.
**Invariant:** the preview is always ≤ both limits including the marker; media never counts against the text bound; the full text is on disk before the preview is returned; a failed write fails the tool settlement; wx flag makes spill files collision-proof.
**Probe:** `packages/core/test/tool-output-store.test.ts` (10 `it.live` cases): "bounds the provider-facing text channel with one managed file" pins full-text-on-disk + preview ≤ MAX_BYTES; "preserves native media and structured metadata without applying a settlement media limit" pins a 6MB data URI passing through untouched with empty outputPaths; "fails oversized settlement when complete retention cannot be written" pins StorageError when the managed dir is a file; "honors configured limits" pins the config override path; "cleans expired managed files and preserves unrelated files" pins mtime cutoff + non-tool_ preservation. Source pin:
```bash
grep -c 'flag: "wx"' packages/core/src/tool-output-store.ts   # expect 1
grep -n 'output truncated' packages/core/src/tool-output-store.ts   # expect 1 (:159)
grep -c 'Schedule.spaced' packages/core/src/tool-output-store.ts   # expect 1
grep -n 'resources.bound' packages/core/src/tool/registry.ts   # expect 1 (:75)
```

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "opencode", query: "ToolOutputStore bound outputPaths wx flag retention preview marker settleWith", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the text-only bound with media passthrough and complete-retention-before-preview ordering; adopt wx-flag managed spill + marker-budgeted head/tail preview; adopt fail-the-settlement on retention write failure (never ship lossy output silently); adopt one global hourly retention loop with a 7-day mtime cutoff. Adapt the limits/config shape and the ascending-id file naming to your store; omit the JSON.stringify structured fallback if your tool outputs always carry text. Direct tests read whole (tool-output-store.test.ts 247L); bun runner blocked at this checkout, probes are byte-exact greps.
