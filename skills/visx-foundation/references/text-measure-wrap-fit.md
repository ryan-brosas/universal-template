<!-- capsule-v2 -->
# SVG text measurement + wrapping — how do you wrap text without DOM layout, and shrink-to-fit without growing?

**Source:** visx (ui-visx) MIT `master@485c0359664ee8e612992defb16e1f035ed40b23`; Codebase Memory `ext-ui-visx`. **Question:** How are words measured, lines accumulated, vertical anchor computed, and why does `scaleToFit: true` differ from `'shrink-only'`?

## Canvas-measured greedy wrap + CSS-calc dy
**Path/Symbol:** `packages/visx-text/src/hooks/useText.ts:useText` (:19–121); width util `util/getStringWidth.ts` (canvas `measureText`).
**Signature:** `useText(props) => {wordsByLines: {words, width?}[], startDy: string, transform: string}`.
**Data Shape:** split regex preserves NBSP as non-breaking: `/(?:(?!\u00A0+)\s+)/`; space width measured via `getStringWidth('\u00A0')`.

### Decisive source
```ts
if (currentLine &&
    (width == null || scaleToFit || (currentLine.width||0) + wordWidth + spaceWidth < width)) {
  currentLine.words.push(word); currentLine.width += wordWidth + spaceWidth;
} else {
  result.push({ words: [word], width: wordWidth });
}

// scaleToFit matrix — origin-corrected so x,y stay anchored
const sx = scaleToFit === 'shrink-only' ? Math.min(width / lineWidth, 1) : width / lineWidth;
transforms.push(`matrix(${sx}, 0, 0, ${sy}, ${originX}, ${originY})`);
```
```ts
// verticalAnchor via reduce-css-calc (capHeight default '0.71em')
verticalAnchor === 'middle'
  ? reduceCSSCalc(`calc(${(wordsByLines.length-1)/2} * -${lineHeight} + (${capHeight} / 2))`)
```

**Flow:** measure words once (memo on children+style) → greedy accumulate into lines ONLY when `width` or `scaleToFit` set (single-line fast path skips measuring consumers) → compute `startDy` per anchor (`start`: capHeight; `middle`: centered stack; `end`: negative stacked height) → optional scale matrix + rotation compose the transform string.
**Invariant:** bare `scaleToFit: true` GROWS small text up to `width`; `'shrink-only'` caps at 1× — choosing the wrong one distorts axis labels. The wrap predicate is strict `<` (a line exactly at width wraps). Invalid/NaN x/y short-circuit ALL outputs to empty strings.
**Probe:** `packages/visx-text/test/Text.test.tsx :153 ("Does not scale above 1 when scaleToFit is set to 'shrink-only'") / :169 ("Shrinks long text…")`.

## Get live surrounding code
**Retrieve:**
```ts
// 'startDy' is not a graph token (local variable) — query the hook instead:
await mcp.codebase_memory.search_graph({ project: "ext-ui-visx", query: "useText verticalAnchor", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt measurement + wrap + anchor math; adapt capHeight/lineHeight defaults to your typography; omit reduce-css-calc if you can compute em-maths natively (keep the SVG-matrix origin correction).
