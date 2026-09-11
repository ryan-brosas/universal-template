<!-- capsule-v2 -->
# Editing — the ordered replacer chain behind one replace()

**Source:** opencode MIT `<branch>@<commit>`; Codebase Memory `opencode`. **Question:** how does a model-driven edit survive fuzzy, multi-occurrence, or corrupted finds without corrupting untouched bytes?

## Connected graph-selected seam
**Path/Symbol:** `packages/opencode/src/tool/edit.ts`: `EditTool` (:58), `SimpleReplacer` (:244), `LineTrimmedReplacer` (:248), `BlockAnchorReplacer` (:288), `WhitespaceNormalizedReplacer` (:427), `IndentationFlexibleReplacer` (:471), `EscapeNormalizedReplacer` (:499), `MultiOccurrenceReplacer` (:548), `TrimmedBoundaryReplacer` (:562).
**Signature:** `replace(content, oldString, newString, replaceAll)` iterates an ordered list of replacer generators; the first producing a USABLE, UNIQUE span wins.
**Data Shape:** replacers are generator functions yielding candidate match spans (with original-text offsets); uniqueness = `indexOf === lastIndexOf`; non-unique candidates demote to the next replacer.

### Decisive source
```ts
export const LineTrimmedReplacer: Replacer = function* (content, find) {
  // compares trim()-ed lines but yields the ORIGINAL untrimmed span
  // by recomputing character offsets from line lengths (:266-286)
}
export const BlockAnchorReplacer: Replacer = function* (content, find) {
  // requires >=3 search lines, anchors on trimmed first/last lines,
  // bounds block-size drift to max(1, floor(searchBlockSize*0.25)) (:309),
  // scores middle lines by Levenshtein similarity at 0.65 threshold (:338-404)
}
```

**Flow:** exact `SimpleReplacer` first; then increasingly tolerant matchers (line-trimmed, block-anchor, whitespace/indentation/escape-normalized, trimmed-boundary, multi-occurrence). Each yields original-text spans so replacement never corrupts untouched bytes. A disproportionate-span guard (:731-735) rejects fuzzy spans far larger than requested; no-replacer → not-found, candidates-but-none-unique → multiple-matches (both action-instructing errors).
**Invariant:** exact matches always win before any fuzzy heuristic; replacement preserves file encoding (CRLF/LF detected :15-17, normalized then converted back :128-131; BOM `desiredBom = source.bom || next.bom` :133); the whole read-modify-write runs under a per-path `Semaphore(1)` (:35-41, :88).
**Probe:** `packages/opencode/test/tool/edit.test.ts` (indented/CRLF find succeeds via LineTrimmed/EscapeNormalized; 3+-line find succeeds only at >=0.65 similarity; twice-occurring oldString without replaceAll throws "Found multiple matches…").

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "opencode", query: "Replacer replace edit tool BlockAnchor similarity", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the ordered replacer-generator pipeline (exact-first, then tolerant matchers yielding original-text spans) with uniqueness demotion and disproportionate-span refusal; adapt the replacer set and similarity threshold to host; omit the Effect/Semaphore transaction wiring unless the target is concurrent.
