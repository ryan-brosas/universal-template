<!-- capsule-v2 -->
# Editable-region sizing ladder — window margins for partial mode, token-budget symmetric growth with rollback quirk

**Source:** Continue (Apache-2.0) `main@5522c6f44ca0ac3528b37244818fbfa39b5af470`; Codebase Memory `continue`. **Question:** How big is the region the model may rewrite in each mode, and what are the exact growth/stop rules of the token-budget expander?

## Key facts
**Path/Symbol:** `core/nextEdit/providers/BaseNextEditProvider.ts` — `calculateOptimalEditableRegion(helper, maxTokens=512, heuristic="tokenizer")` (:382-460); overrides `InstinctProvider.calculateEditableRegion` (providers/InstinctNextEditProvider.ts:135-154), `MercuryCoderProvider.calculateEditableRegion` (providers/MercuryCoderNextEditProvider.ts:126-145); window constants `getWindowSize()` — Instinct {top:1,bottom:5}, Mercury {top:0,bottom:5}.
**Signature:** `calculateEditableRegion(helper, usingFullFileDiff) → {editableRegionStartLine, editableRegionEndLine}`.
**Data Shape:** two modes: partial (`usingFullFileDiff=false`) → cursor ± fixed margins clamped to file; full → `calculateOptimalEditableRegion(helper, 512, "tokenizer")`.

### Decisive source
```ts
// :404-453 — alternating above/below growth; the rollback quirk:
while (totalTokens < maxTokens) {
  let addedLine = false;
  if (addingAbove) {
    if (editableRegionStartLine > 0) {
      editableRegionStartLine--;                 // grow up FIRST, unconditionally counted
      totalTokens += lineTokens(fileLines[editableRegionStartLine]);
      addedLine = true;
    }
  } else { /* mirror for bottom */ }
  if (!addedLine) {
    if (start === 0 && end === fileLines.length - 1) break;  // whole file enclosed
    addingAbove = !addingAbove;                   // exhausted one side? flip
    continue;
  }
  if (totalTokens > maxTokens) {
    if (addingAbove) editableRegionStartLine++;   // UNDO the last added line…
    else editableRegionEndLine--;
    break;                                        // …but its tokens STAY in totalTokens (harmless: we exit)
  }
  addingAbove = !addingAbove;
}
```

**Flow:** tokenizer heuristic counts each candidate line with `countTokens(line, helper.modelName)` (falls back to `Math.ceil(len/4)` under `"fourChars"`); growth alternates up/down one line at a time starting from the cursor's own line (its tokens seed `totalTokens`); when a side hits a file boundary the alternation flips to keep growing the other side until both are exhausted (region = whole file). Instinct additionally CLAMPS the computed editable region into a ±25-line prompt window inside `buildPromptContext` (windowStart/windowEnd) — sizing and prompt-windowing are separate concerns.

**Invariant:** the budget check happens AFTER adding a line, so the region can overshoot `maxTokens` by at most the last line and is then rolled back ONE line on the side just grown — but only that side. The loop terminates either by budget rollback or by enclosing the entire file. Margins are per-model data (`getWindowSize`), not globals: porting Mercury's topMargin=0 onto Instinct-style prompts shifts every editable region one line.

**Probe:** `grep -c 'calculateOptimalEditableRegion' core/nextEdit/providers/BaseNextEditProvider.ts core/nextEdit/providers/InstinctNextEditProvider.ts core/nextEdit/providers/MercuryCoderNextEditProvider.ts` → 1+1+1=3 lines (each override's call is `this.calculateOptimalEditableRegion`, one hit per file); `grep -c 'addingAbove = !addingAbove' core/nextEdit/providers/BaseNextEditProvider.ts` → 2 (:440 flip-on-exhausted-side, :453 alternating toggle); `grep -c 'topMargin: 1' core/nextEdit/providers/InstinctNextEditProvider.ts` → 1; `grep -n 'topMargin: 0' core/nextEdit/providers/MercuryCoderNextEditProvider.ts` → :32.

**Retrieve:** `await mcp.codebase_memory.search_graph({ project: "continue", query: "calculateOptimalEditableRegion calculateEditableRegion getWindowSize", limit: 8 })`

## Verdict
Adopt mode-split sizing: cheap margins for partial rewrites, tokenizer-budgeted symmetric expansion for full-file models. Reproduce the post-add budget test + single-line rollback exactly; treat per-model margins as model config, never hardcode.
