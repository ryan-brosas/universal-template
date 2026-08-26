<!-- capsule-v2 -->
# Single-line completion — diff-pattern classification for midline insertions vs end-of-line

**Source:** Continue (Apache-2.0) `main@5522c6f44ca0ac3528b37244818fbfa39b5af470`; Codebase Memory `continue`. **Question:** When the cursor is MIDLINE, how does Continue decide whether a completion replaces the rest of the line, inserts without repeating, or is a plain end-of-line insert — and how does it compute the replacement range?

## Diff-pattern classification
**Path/Symbol:** `core/autocomplete/util/processSingleLineCompletion.ts:processSingleLineCompletion` (41–93).
**Signature:** `processSingleLineCompletion(lastLineOfCompletionText, currentText, cursorPosition): SingleLineCompletionResult | undefined`.
**Data Shape:** `SingleLineCompletionResult = {completionText, range?: {start, end}}`; uses `Diff.diffWords(currentText, lastLineOfCompletionText)` producing `DiffType[]` with `added`/`removed`/`value`.

### Decisive source
```ts
const diffs = Diff.diffWords(currentText, lastLineOfCompletionText);
if (diffPatternMatches(diffs, ["+"])) return { completionText: lastLineOfCompletionText };                    // pure insert, at end of line
if (diffPatternMatches(diffs, ["+","="]) || diffPatternMatches(diffs, ["+","=","+"]))
  return { completionText: lastLineOfCompletionText, range: { start: cursorPosition, end: currentText.length + cursorPosition } }; // model repeated text after cursor to EOL
if (diffPatternMatches(diffs, ["+","-"]) || diffPatternMatches(diffs, ["-","+"]))
  return { completionText: lastLineOfCompletionText };                                                        // midline insert, no repeat to EOL
if (diffs[0]?.added) return { completionText: diffs[0].value };                                              // first added part only
return { completionText: lastLineOfCompletionText };                                                          // default simple insert
```

**Flow:** `diffWords` compares the current line text against the model's last-line completion. The resulting diff pattern classifies the edit: `["+"]` = pure insertion at EOL; `["+","="]`/`["+","=","+"]` = the model repeated the text after the cursor to the end of the line (so the completion REPLACES that range — `range.start=cursorPosition`, `range.end=currentText.length+cursorPosition`); `["+","-"]`/`["-","+"]` = midline insert without repeating to EOL (no range); otherwise use the first added part or default to simple insertion.

**Invariant:** the `["+","="]` / `["+","=","+"]` patterns are the ONLY cases that set a replacement `range` — meaning the model echoed the suffix text and the ghost must overwrite it rather than append; all other patterns return a plain `completionText` with no range (pure insert). `diffPatternMatches` requires exact diff-length and per-part type equality.

**Probe:** `core/autocomplete/util/processSingleLineCompletion.vitest.ts` — "should handle simple end of line completion", "should handle midline insert repeating the end of line", "should handle midline insert repeating the end of line plus adding a semicolon", "should handle simple midline insert", "should handle complex diff with addition in the beginning", "should handle simple insertion even with random equality".

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "continue", query: "processSingleLineCompletion diffPatternMatches", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the diff-pattern→(completionText, range) classification and the exact `["+","="]`/`["+","=","+"]` replacement-range rule; adapt nothing host-specific; omit the diff library choice (any word-diff works). Coverage caveat: graph metadata `metadata_match`; direct vitest suite.
