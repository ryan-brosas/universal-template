<!-- capsule-v2 -->
# Markdown mock-capture protocol — How does a regex header parser feed a tree-sitter-shaped pipeline without a grammar?

**Source:** Roo-Code Apache-2.0 `main@b867ec9145750d0ae1ff7f02d35406e9bf2a0b16`; Codebase Memory project `Roo-Code`. **Question:** When one language in your outline pipeline has no tree-sitter grammar, how do you fake the capture interface so the shared downstream stays untouched — and which capture fields must you synthesize?

## Connected graph-selected seam
**Path/Symbol:** `src/services/tree-sitter/markdownParser.ts:parseMarkdown` (:38-184); legacy formatter `formatMarkdownCaptures` (:194-227); integration point `parseSourceCodeDefinitionsForFile` markdown branch (`src/services/tree-sitter/index.ts:115-137`).
**Signature:** `function parseMarkdown(content: string): QueryCapture[]`; `function formatMarkdownCaptures(captures: QueryCapture[], minSectionLines = 4): string | null`.
**Data Shape:** Emits MockCapture objects cast to `QueryCapture[]`: `{ node: { startPosition:{row}, endPosition:{row}, text, parent? }, name, patternIndex }`. Each ATX/setext header yields a PAIR of captures sharing one node: `name.definition.header.h<level>` + `definition.header.h<level>`. Section ranges are MUTATED after collection: each header's `endPosition.row` becomes (next header's start − 1), last header extends to `lines.length - 1`.

### Decisive source
```ts
// Update end positions for section ranges
for (let i = 0; i < headerCaptures.length; i++) {
	const headerPair = headerCaptures[i]
	if (i < headerCaptures.length - 1) {
		// End position is the start of the next header minus 1
		const nextHeaderStartRow = headerCaptures[i + 1][0].node.startPosition.row
		headerPair.forEach((capture) => {
			capture.node.endPosition.row = nextHeaderStartRow - 1
		})
	} else {
		// Last header extends to the end of the file
		headerPair.forEach((capture) => {
			capture.node.endPosition.row = lines.length - 1
		})
	}
}
```

**Flow:** empty/whitespace-only content → `[]` → per line: ATX match `/^(#{1,6})\s+(.+)$/` pushes the capture pair; setext underlines require ≥3 `=` or `-` AND the previous line passing `/^\s*[^#<>!\[\]`\t]+[^\n]$/` (plain-text guard rejecting headers/code/special lines) with node spanning rows `i-1..i` → sort by start row → pair up consecutive captures two-by-two → rewrite end positions into section ranges → return flattened array. The markdown branch in index.ts then runs the SAME `processCaptures` used for real grammars; the `name.definition.*` captures hit the component-name path and emit every header regardless of min-lines... except that section ranges make spans large anyway.

**Invariant:** Four porting-critical facts: (a) the pair-per-header structure is LOAD-BEARING for the downstream walk — `processCaptures` resolves name-captures through `node.parent` (absent on mocks ⇒ `null` ⇒ skip) but ALSO accepts plain `definition.*` captures directly, so each pair guarantees at least one surviving emit per header; the legacy `formatMarkdownCaptures` instead iterates ODD indices only (`i=1; i+=2`) — it hardcodes "definition capture is the second of every pair" and breaks if pairing ever changes (it's kept for backward compat, not on the main path); (b) section ranges are computed by MUTATING node end positions AFTER sort — a porter who treats captures as immutable loses whole-section outlines and gets single-line headers filtered by any min-span gate; (c) setext detection needs BOTH regexes — underline alone would classify horizontal rules and table separators as H2s; (d) the mock satisfies exactly the four fields processCaptures reads (`startPosition.row`, `endPosition.row`, `text`, `parent`, plus `name`) — anything else the real QueryCapture carries is dead weight here.

**Probe:** `src/services/tree-sitter/__tests__/markdownIntegration.spec.ts` (mocked fs, REAL pipeline): `parseSourceCodeDefinitionsForFile("test.md")` returns `"# test.md"` + exact ranges `1--5 | # Main Header`, `6--10 | ## Section 1`, `11--15 | ### Subsection 1.1`, `16--20 | ## Section 2`; headerless content returns `undefined`. Unit-level: `markdownParser.spec.ts` covers parseMarkdown/formatMarkdownCaptures directly.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Roo-Code", query: "parseMarkdown", limit: 5 });
// → Roo-Code.src.services.tree-sitter.markdownParser.parseMarkdown Function src/services/tree-sitter/markdownParser.ts 38-184
```

## Verdict
Adopt the duck-typing move itself: when adding a grammarless format to an AST pipeline, synthesize ONLY the capture fields the shared processor reads and keep the name grammar (`name.definition.*` + `definition.*`) identical so no downstream branch forks. Adapt header regexes to your dialect (setext guards especially). Omit `formatMarkdownCaptures` unless you need the legacy output shape — its odd-index coupling is documented as a hazard, not a pattern.
