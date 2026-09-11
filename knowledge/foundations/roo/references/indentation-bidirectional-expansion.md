<!-- capsule-v2 -->
# indentation bidirectional expansion — how do you extract a complete semantic block from raw text with no parser?

**Source:** Roo-Code Apache-2.0 `main@b867ec9145750d0ae1ff7f02d35406e9bf2a0b16`; Codebase Memory `Roo-Code`. **Question:** What is the exact expansion algorithm that guarantees "complete, syntactically valid code blocks" from whitespace alone, and where are its edge behaviors pinned?

## readWithIndentation — Codex-style anchor expansion
**Path/Symbol:** `src/integrations/misc/indentation-reader.ts:readWithIndentation` (288–424) fed by `parseLines` (110–139), `computeEffectiveIndents` (145–158), `formatWithLineNumbers` (230–247), `computeIncludedRanges` (252–275).
**Signature:** `function readWithIndentation(content: string, options: IndentationReadOptions): IndentationReadResult` with `{anchorLine, maxLevels?=0, includeSiblings?=false, includeHeader?=true, limit?=2000, maxLines?}`.
**Data Shape:** `LineRecord {lineNumber(1-based), content, indentLevel, isBlank, isBlockStart}`; result `{content(numbered string), includedRanges([start,end][]), totalLines, returnedLines, wasTruncated}`. Indent math: tab=4 spaces (`TAB_WIDTH`), `indentLevel = floor(indentSpaces / INDENT_SIZE=4)`.

### Decisive source
```ts
// Bidirectional expansion from anchor (Codex algorithm)
const result: LineRecord[] = [lines[anchorIdx]]
let i = anchorIdx - 1 // Up cursor
let j = anchorIdx + 1 // Down cursor
let iMinCount = 0 // Count of min-indent lines seen going up
let jMinCount = 0 // Count of min-indent lines seen going down

while (result.length < finalLimit) {
    let progressed = false
    // Expand upward …
    if (i >= 0 && effectiveIndents[i] >= minIndent) {
        result.unshift(lines[i]); progressed = true
        if (effectiveIndents[i] === minIndent && !includeSiblings) {
            const allowHeader = includeHeader && isComment(lines[i])
            const canTake = allowHeader || iMinCount === 0
            if (canTake) { iMinCount++ }
            else { result.shift(); progressed = false; i = -1 } // stop up
        }
        if (i >= 0) i--
    } else if (i >= 0) { i = -1 }
    // … downward mirror: first min-indent line kept (jMinCount 0→1),
    // second one popped and down-expansion stops.
    if (!progressed) break
}
trimEmptyLines(result)
const wasTruncated = result.length >= finalLimit || i >= 0 || j < lines.length
```

**Flow:** parse → blank lines inherit previous non-blank indent (`computeEffectiveIndents`) → validate `anchorLine ∈ [1,totalLines]`, else return the error STRING as content with empty ranges (no throw) → `minIndent = maxLevels===0 ? 0 : max(0, anchorIndent − maxLevels)` → `finalLimit = min(limit, maxLines ?? limit, totalLines)`; `finalLimit===1` short-circuits to the single anchor line → alternate up/down one line per loop iteration; a line whose effective indent drops below minIndent stops that direction → trim blank edges → number and merge contiguous ranges.
**Invariant:** (1) Sibling exclusion keeps AT MOST ONE min-indent boundary line per side when `includeSiblings=false` — the counter rejects the SECOND sibling block, so the block containing the anchor stays closed without swallowing its neighbors. (2) `includeHeader` does NOT prepend imports; it lets COMMENT lines at exactly minIndent bypass the upward sibling counter (kernel spec documents this explicitly at indentation-reader.spec.ts:404–420). (3) `wasTruncated = (hit limit OR either cursor unexhausted) AND returnedLines < totalLines`. (4) Output numbers pad to the width of the LAST included line's number and long lines cut at MAX_LINE_LENGTH−3+`...`. (5) maxLevels=0 means unlimited upward reach (whole enclosing file context reachable).
**Probe:** runner BLOCKED (no node_modules). Direct spec exists and pins the real kernel: `src/integrations/misc/__tests__/indentation-reader.spec.ts` — offset-beyond-end error content (282–287), invalid anchors low/high → content "Error" + returnedLines 0 (533–553), limit=1 single line (570–581), maxLevels 0-vs-1 whole-file scoping (337–374), includeHeader comment nuance (404–420). Deterministic source pin: `grep -c 'Count of min-indent lines seen going up' src/integrations/misc/indentation-reader.ts` → 1.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Roo-Code", qn_pattern: ".*indentation-reader.*", fields: ["lines"], format: "json", limit: 20 });
```

## Verdict
Adopt as the parser-free block extractor for any host that must show "the whole function" given only a hit line number; keep the two-cursors-plus-counter shape or you will re-derive sibling leakage. Adapt INDENT_SIZE/TAB_WIDTH and BLOCK_START_PATTERNS/HEADER_PATTERNS language coverage to your target languages. Omit nothing silently: the anchor-out-of-range error-as-content contract is what ReadFileTool's UI copy depends on. Direct spec present at pin (this is the plane's best-tested kernel).
