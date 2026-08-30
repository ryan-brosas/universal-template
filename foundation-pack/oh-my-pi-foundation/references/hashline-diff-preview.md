<!-- capsule-v2 -->
# Hashline diff preview — how do you turn a signed numbered diff into a post-edit preview a model can re-anchor against?

**Source:** Oh My Pi MIT `main@96f42809764f0907f7d6b115eab5710de28941de`; Codebase Memory `oh-my-pi`. **Question:** How do you convert a `+N|` / `-N|` / ` N|` unified diff into compact current-file line numbers that a follow-up edit can anchor on directly?

## Signed-diff renumbering with added-run elision
**Path/Symbol:** `packages/hashline/src/diff-preview.ts:buildCompactDiffPreview` (76–124); helpers `parseNumberedDiffLine` (48–60), `appendAddedRun` (62–74), `appendPreviewLine` (26–35); types `CompactDiffPreview` / `CompactDiffOptions` (`types.ts:148–160`).
**Signature:** `function buildCompactDiffPreview(diff: string, options?: CompactDiffOptions): CompactDiffPreview`.
**Data Shape:** input lines are `<sign><lineNum>|<content>` with sign ∈ {`+`, `-`, `␣`} — external producers number `+` lines with the POST-edit line number and `-`/context lines with the PRE-edit number. Options `{ maxAddedRunContext?: number, maxUnchangedRun?: number }` (alias; default 2, floored at 1 by `Math.max(1, Math.trunc(v))`). Output `{ preview: string, addedLines: number, removedLines: number }`.

### Decisive source
```ts
// External producers number context lines with the PRE-edit number; convert
// them to post-edit positions with the running offset as we walk the diff.
default: {
    flushAddedRun();
    const newLineNumber = parsed.lineNumber + addedLines - removedLines;
    appendPreviewLine(formatted, `${newLineNumber}:${parsed.content}`);
}
// Long contiguous added runs collapse to head, one elision marker, tail.
function appendAddedRun(output: string[], run: string[], edgeLines: number): void {
    const collapseThreshold = edgeLines * 2 + 1;
    if (run.length <= collapseThreshold) { for (const t of run) appendPreviewLine(output, t); return; }
    for (let i = 0; i < edgeLines; i++) appendPreviewLine(output, run[i]);
    appendPreviewLine(output, PREVIEW_ELISION_MARKER);          // "…"
    for (let i = run.length - edgeLines; i < run.length; i++) appendPreviewLine(output, run[i]);
}
```

**Flow:** split diff on `\n` (empty ⇒ no lines) → parse each row; unparseable lines pass through verbatim after flushing the pending added-run buffer → `+` rows accumulate (post-edit numbers preserved) into a run buffer; `-` rows increment `removedLines` and are OMITTED from output; context rows flush the run then emit with the offset-converted number → final flush, then trim leading/trailing separator rows.
**Invariant:** removed content never appears in the preview but always increments `removedLines`; every emitted `N:` is a 1-indexed position in the POST-edit file, so a follow-up hashline edit can reuse visible concrete lines directly; separators (`…`, blank gap rows) never stack, never lead, never trail.
**Probe:** `packages/hashline/test/diff-preview.test.ts:15` ("renumbers context lines against the post-edit file after range expansion" ⇒ `["1:a1","2:a2","3:X","4:Y","5:Z","6:a5","7:a6","8:a7"]`); `:22` (7-line added run collapses to head/`…`/tail with counts intact); `:38` (blank gap rows deduped when removals make them adjacent, edge separators trimmed).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", name_pattern: "^buildCompactDiffPreview$", limit: 5, fields: ["signature"] });
await mcp.codebase_memory.get_code_snippet({ project: "oh-my-pi", qualified_name: "oh-my-pi.packages.hashline.src.diff-preview.buildCompactDiffPreview" });
```

## Verdict
Adopt the `<sign><lineNum>|` grammar tolerance, the running-offset context renumbering, and the edge-collapsing added-run elision (counts always exact, preview always re-anchorable); adapt cap defaults and marker glyphs to your UI; omit nothing structural — the module is deliberately decoupled from the diff producer. Consumer contract worth porting together: `packages/coding-agent/src/edit/hashline/execute.ts:166` feeds the generated diff straight into this preview and composes `header + block resolutions + move note + preview + warnings` as one tool text, and `packages/coding-agent/src/edit/diff.ts:167` documents that boundary lines honor this exact renumbering contract.
