<!-- capsule-v2 -->
# retired-header-reflow — how do already-committed hard rows survive a terminal resize without being recomposed?

**Source:** oh-my-pi MIT `main@2b66ee69f2`; Codebase Memory `oh-my-pi`. **Question:** When the accepted header rows were wrapped at width W, what must a resize frame show at width W′ — and what changes inside tmux?

## #reflowRetiredHeader
**Path/Symbol:** `packages/coding-agent/src/modes/composer.ts` (`#reflowRetiredHeader`, `#retiredHeaderRows`, `#retiredHeaderStart`, `renderResizeFrame`).
**Signature:** `#reflowRetiredHeader(width: number, start: number): string[]`; resize path seeds `#resizeRetiredHeaderStart ??= max(0, #retiredHeaderStart - max(0, rows - #lastNormalRows))`.
**Data Shape:** Input = exact accepted hard rows (ANSI-bearing strings); output = re-wrapped slices via `sliceWithWidth(line, column, columns, true)` with a zero-width fallback; multiplexer ⇒ plain `lines.slice(start)`.

### Decisive source
```ts
if (isInsideTerminalMultiplexer()) return lines.slice(start);
const reflowed: string[] = [];
const columns = Math.max(1, width);
for (let index = start; index < lines.length; index++) {
	const line = lines[index]!;
	const lineWidth = visibleWidth(line);
	if (lineWidth === 0) { reflowed.push(""); continue; }
	for (let column = 0; column < lineWidth; ) {
		let slice = sliceWithWidth(line, column, columns, true);
		if (slice.width === 0) slice = sliceWithWidth(line, column, columns);
		reflowed.push(slice.text);
		column += Math.max(1, slice.width);
	}
}
```

**Flow:** A wider terminal NEVER joins hard tip wraps committed at the original width — the alt/resize buffer repaints the stored rows re-wrapped exactly as the restored native buffer will, so the transient frame matches what history will look like. Inside a multiplexer the terminal itself reflows scrollback, so the composer only CLIPS (`slice(start)`) and lets the suffix disappear rather than fighting the host. The first resize may pull part of the prefix down before the normal buffer is borrowed (`#lastNormalRows` delta).
**Invariant:** Reflow is deterministic row-slicing with wide-glyph safety (a glyph straddling the boundary stays whole — pinned by the `界` test); never regenerate header content at the new width.
**Probe:** `grep -nF 'isInsideTerminalMultiplexer()) return lines.slice(start)' packages/coding-agent/src/modes/composer.ts` → line `364`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "reflowRetiredHeader retiredHeaderRows sliceWithWidth resize", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt hard-row preservation + multiplexer clip; adapt sliceWithWidth to your width measure; omit the CPR-settle dance if your scheduler differs. Direct tests: welcome-history-resize "preserves a wide glyph that straddles a retired-row resize boundary" and "clips retired hard rows instead of reflowing them inside a multiplexer".
