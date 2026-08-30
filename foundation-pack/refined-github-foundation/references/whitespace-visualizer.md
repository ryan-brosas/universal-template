<!-- capsule-v2 -->
# show-whitespace-on-line — how do you visualize invisible characters inside syntax-highlighted lines without corrupting the DOM you're iterating?

**Source:** refined-github MIT `main@3bbe6088fe301d0d5cf1ae751a49307005762a68`; Codebase Memory `refined-github`. **Question:** When each code line is a sequence of highlighter-generated text nodes, what is the safe split-and-wrap order for whitespace runs, and which nodes must be skipped?

## Reverse-index splitText wrapping with boundary-node rules
**Path/Symbol:** `source/helpers/show-whitespace-on-line.tsx:showWhiteSpacesOnLine` (:6–61); node source `source/helpers/get-text-nodes.ts:getTextNodes` (:1–14).
**Signature:** `showWhiteSpacesOnLine(line: Element, shouldAvoidSurroundingSpaces = false): Element`; `getTextNodes(element: Node): Text[]` (TreeWalker, `NodeFilter.SHOW_TEXT`, do/while collection).
**Data Shape:** Returns the same `line` element, mutated in place. Wraps whitespace runs in `<span data-rgh-whitespace="space|tab">` for CSS `::before` visualization.

### Decisive source
```ts
const textNodesOnThisLine = getTextNodes(line);
for (const [nodeIndex, textNode] of textNodesOnThisLine.entries()) {
	let text = textNode.textContent;   // cached read — #2737
	if (text.length > 1000) continue;  // perf guard — #5092
	const isLeading = nodeIndex === 0;
	const isTrailing = nodeIndex === textNodesOnThisLine.length - 1;
	// …leading/trailing char exclusion when shouldAvoidSurroundingSpaces…
	for (let index = endingCharacterIndex; index >= startingCharacterIndex; index--) {
		// find run of same char, then:
		if (endingIndex < text.length - 1) textNode.splitText(endingIndex + 1);
		textNode.splitText(index);
		text = textNode.textContent;      // re-cache AFTER mutation
		textNode.after(<span data-rgh-whitespace=…>{textNode.nextSibling}</span>);
	}
}
```

**Flow:** collect all text nodes on the line → per node, scan RIGHT-to-LEFT (reverse index) so earlier `splitText` offsets stay valid without bookkeeping → group runs of the identical character → split off the run's tail then head → move the isolated whitespace-only node into a marker span via `textNode.after(...)`. Leading/trailing boundary nodes get special treatment when `shouldAvoidSurroundingSpaces` (skip first char of first node / last char of last node — they delimit the code).
**Invariant:** (1) `textContent` must be RE-READ after every split (the cached string is stale the moment `splitText` runs — #2737 exists because someone cached it once); (2) reverse iteration is load-bearing — forward iteration needs offset adjustment after each split; (3) non-boundary SINGLE spaces between visible chars are skipped (`index === endingIndex && thisCharacter === ' '` guard) so normal prose spacing isn't dotted with markers; (4) >1000-char nodes skipped entirely (#5092 perf).
**Probe:** `source/helpers/show-whitespace-on-line.test.ts:5+` drives real highlight.js output through `process()` and pins the exact serialized HTML (spaces→•, tabs→⟶) across leading/trailing/mixed-run cases.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "refined-github", query: "showWhiteSpacesOnLine", limit: 10 });
// → refined-github.source.helpers.show-whitespace-on-line.showWhiteSpacesOnLine Function source/helpers/show-whitespace-on-line.tsx 6-61
```

## Verdict
Adopt the reverse-splitText algorithm + re-cache rule + boundary-node semantics for any whitespace/tab visualization over highlighted code (works on any host whose highlighter emits multi-text-node lines). Adapt the marker attribute name and CSS rendering. Omit the >1000-char bail at your peril — it's a real-page perf guard, not a nicety.
