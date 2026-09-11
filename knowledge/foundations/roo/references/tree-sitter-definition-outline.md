<!-- capsule-v2 -->
# Tree-sitter definition extraction — How do raw AST captures become a deduplicated, line-ranged outline an LLM can read?

**Source:** Roo-Code Apache-2.0 `main@b867ec9145750d0ae1ff7f02d35406e9bf2a0b16`; Codebase Memory project `Roo-Code`. **Question:** Given tree-sitter query captures over a file, how do you turn them into a stable "start--end | first-line" outline without duplicating ranges, leaking HTML noise, or misnumbering lines?

## Connected graph-selected seam
**Path/Symbol:** `src/services/tree-sitter/index.ts:processCaptures` (:184-284); entry `parseSourceCodeDefinitionsForFile` (:97-149); internal `parseFile` (:294-331); module mutable knob `currentMinComponentLines`/`getMinComponentLines`/`setMinComponentLines` (:10-27).
**Signature:** `function processCaptures(captures: QueryCapture[], lines: string[], language: string): string | null`; `async function parseSourceCodeDefinitionsForFile(filePath: string, rooIgnoreController?: RooIgnoreController): Promise<string | undefined>`.
**Data Shape:** Output is one line per kept definition: `<1-based start>--<1-based end> | <raw source line at start>`; `null` when nothing survives; callers wrap as `# <basename>\n<body>` (:134, :145). Capture contract: only captures whose `name` contains `definition` or `name` are considered; `@definition.X` captures carry the whole node, `@name.definition.X` captures resolve via `node.parent`. Minimum size knob defaults to 4 lines (`DEFAULT_MIN_COMPONENT_LINES_VALUE`), mutable ONLY for tests.

### Decisive source
```ts
// Sort captures by their start position
captures.sort((a, b) => a.node.startPosition.row - b.node.startPosition.row)

const processedLines = new Set<string>()
captures.forEach((capture) => {
	const { node, name } = capture
	if (!name.includes("definition") && !name.includes("name")) return
	const definitionNode = name.includes("name") ? node.parent : node
	if (!definitionNode) return
	const startLine = definitionNode.startPosition.row
	const endLine = definitionNode.endPosition.row
	const lineCount = endLine - startLine + 1
	if (lineCount < getMinComponentLines()) return
	const lineKey = `${startLine}-${endLine}`
	if (processedLines.has(lineKey)) return
```

**Flow:** sort by start row → per capture: skip non-definition names → pick the full-definition node (`node` itself, or `node.parent` for name-captures) → drop spans under the min-lines floor → dedupe on the exact `"start-end"` range key → emit `start+1--end+1 | lines[start]` → JSX/TSX extra: filter emitted start lines matching `/^[^A-Z]*<\/?(?:div|span|button|input|h[1-6]|p|a|img|ul|li|form)\b/` UNLESS the capture is a `name.definition` component-name capture (those bypass HTML filtering and are always emitted) → optional parent-context emission: when `node.parent.lastChild` exists and the parent's total span ≥ min lines, also emit the parent's full range under its own dedupe key → parse errors inside `parseFile` are swallowed to `null` (`console.log` + return), so a broken file yields no outline rather than an error.

**Invariant:** Four traps: (a) tree-sitter rows are 0-BASED but the output format is 1-BASED INCLUSIVE — every emitted boundary gets `+ 1`, and dropping that makes outlines off-by-one against the editor gutter (pinned by spec expectations like `1--5 | # Main Header`); (b) dedupe keys are the literal RANGE STRING, not node identity — two differently-named captures of the same span collapse into one line by design, so adding new query patterns cannot inflate the output for overlapping nodes; (c) the min-lines gate applies to the DEFINITION span, computed before any output — with the default floor of 4, trivial getters/setters vanish from outlines (tests lower it to 0 via `setMinComponentLines(0)` in helpers.ts:65, which production code must never call); (d) unsupported extensions never reach here — the extension allowlist (`extensions`, :29-93, ~40 entries incl. `.md`) gates at :110 returning `undefined`.

**Probe:** `src/services/tree-sitter/__tests__/parseSourceCodeDefinitions.javascript.spec.ts` (real wasm + real query through `testParseSourceCodeDefinitions` helper): expects `\d+--\d+ \| class TestClassDefinition {`, methods/getter/setter/object-literal members, arrow functions, decorated classes — i.e. range-format + capture-class coverage per language. Companion `inspect*.spec.ts` files pin per-language trees; `languageParser.spec.ts` pins loader keys.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Roo-Code", query: "processCaptures", limit: 5, fields: ["signature", "name", "file"] });
// → Roo-Code.src.services.tree-sitter.processCaptures Function src/services/tree-sitter/index.ts 184-284
await mcp.codebase_memory.search_graph({ project: "Roo-Code", query: "parseSourceCodeDefinitionsForFile", limit: 5 });
// → Roo-Code.src.services.tree-sitter.parseSourceCodeDefinitionsForFile Function src/services/tree-sitter/index.ts 97-149
```

## Verdict
Adopt the capture→outline pipeline wholesale: definition/name name-gating, parent-resolution for name captures, range-key dedupe, min-span floor, 1-based inclusive emission, and the JSX element filter with its component-name bypass. Adapt the HTML-element regex list and the min-lines default to your host's noise tolerance; adapt the allowlist to your grammars. Omit the VSCode-host file-existence prelude wording. Consumers worth citing: `src/core/condense/foldedFileContext.ts:105` (context folding eats these outlines) and `src/services/code-index/processors/parser.ts:113` (indexing pipeline reuses the loader, not this function). No coverage caveat — directly specced per language.
