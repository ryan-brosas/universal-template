<!-- capsule-v2 -->
# Fuzzy SEARCH/REPLACE applier — how do you apply model-written diff blocks against drifted file content without corrupting indentation?

**Source:** Roo-Code Apache-2.0 `main@b867ec9145750d0ae1ff7f02d35406e9bf2a0b16`; Codebase Memory `Roo-Code`. **Question:** What is the full matching ladder — marker validation, line-number stripping, exact-at-line, buffered middle-out fuzzy, aggressive strip fallback — and the delta/indent rules that keep multi-block edits consistent?

## Marker grammar → sorted blocks → similarity search → indent-transplant replacement
**Path/Symbol:** `src/core/diff/strategies/multi-search-replace.ts` (`MultiSearchReplaceDiffStrategy` :75-546; `applyDiff` :245-520; `getSimilarity` :11-31 normalized Levenshtein ratio; `fuzzySearch` middle-out :37-73; `BUFFER_LINES = 40` :9).
**Signature:** `new MultiSearchReplaceDiffStrategy(fuzzyThreshold?: number /* default 1.0 EXACT; UI inverts: 10% ⇒ 0.9 */, bufferLines?: number)`; `async applyDiff(originalContent, diffContent): Promise<DiffResult>`.
**Data Shape:** Diff blocks = `<<<<<<< SEARCH[\n:start_line:N][\n:end_line:N]\n-------\nsearch\n=======\nreplace\n>>>>>>> REPLACE`, markers escapable with backslash (negative lookbehind), extra `>`s after SEARCH tolerated.

### Decisive source
```ts
const replacements = matches.map(m => ({ startLine: Number(m[2] ?? 0),
        searchContent: m[6], replaceContent: m[7] }))
    .sort((a, b) => a.startLine - b.startLine)          // TOP-DOWN application order
let delta = 0
for (const replacement of replacements) {
    let startLine = replacement.startLine + (replacement.startLine === 0 ? 0 : delta)
    // ladder: exact slice at startLine → ±40-line buffer window → whole-file middle-out
    //          → aggressive line-number-strip retry → structured failure w/ best-match debug
    const originalIndents = matchedLines.map(l => l.match(/^[\t ]*/)[0])
    // relative-indent transplant: replace lines re-indented RELATIVE to the FIRST matched line
    const relativeLevel = currentIndent.length - searchBaseIndent.length
    const finalIndent = relativeLevel < 0
        ? matchedIndent.slice(0, Math.max(0, matchedIndent.length + relativeLevel))
        : matchedIndent + currentIndent.slice(searchBaseLevel)
}
// success even with SOME failed parts: {success:true, content, failParts} when appliedCount>0
```
Similarity is computed on **normalizeString**-ed text (smart quotes/dashes/nbsp collapsed) so vendor-pasted typography still matches; empty search content is rejected (insertions must anchor on a real line); identical search/replace rejected; CRLF detected from original content and used for output.
**Flow:** validateMarkerSequencing → regex-extract all blocks → sort by declared start_line → per block: unescape markers → detect+strip uniform line numbers (deriving startLine from the numbers when none declared) → exact-position similarity check → buffered then global middle-out best-match → optional aggressive strip retry → indent-transplant splice → adjust running `delta` for subsequent declared lines → join with detected line ending.
**Invariant:** Blocks apply top-down with a shared delta so later `:start_line:` values written against pre-edit coordinates still land correctly; partial failure never loses already-applied edits (`failParts` reports them); indentation of replaced code follows the FILE's matched region, not the diff's literal whitespace.
**Probe:** `src/core/diff/strategies/__tests__/multi-search-replace.spec.ts` (:4-132 marker validation matrix incl. merge-conflict ordering, :134-830 exact/indent/CRLF/middle-out cases :772, :831-938 fuzzy (>90% match :837, too-different reject :864, smart quotes :901), :1044-1143 REPLACE-section line-marker rejection + escaped markers).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Roo-Code", query: "MultiSearchReplaceDiffStrategy applyDiff fuzzySearch startLine delta", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the ladder order and the delta bookkeeping exactly — reordering breaks coordinate math; skipping normalizeString re-breaks smart-quote drift. Adapt threshold defaults to your UI's tolerance convention (remember it is INVERTED). Omit the VSCode-specific progress reporting.
