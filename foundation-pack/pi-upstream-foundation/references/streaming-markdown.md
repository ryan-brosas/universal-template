<!-- capsule-v2 -->
# Streaming markdown rendering — how do you render markdown that is still arriving without visible block shrinkage?

**Source:** pi-upstream MIT `main@534bcbffb7e1e7551d9ee3572dfeb278e203e493`; Codebase Memory `pi-upstream`. **Question:** A porter renders token-by-token markdown and code blocks visibly collapse as each backtick of the closing fence arrives — what does pi trim?

## Trim partial closing fences; treat pending math conservatively
**Path/Symbol:** `packages/tui/src/components/markdown.ts` (1,010L; `trimPartialClosingFences` :146-178, applied at :302, issue ref :161).
**Signature:** pre-render token transform: recursively trim partial closing fences (recurring into list items and blockquotes) before handing tokens to the renderer.
**Data Shape:** LaTeX detection guards against eating prose: `$` followed by a space, a digit right after closing, ALL-CAPS env-var-looking content, or a backtick inside ⇒ NOT math. UNCLOSED dollar spans become pending-only when they look like math (`looksLikePendingDollarMath`). Strikethrough is stricter than marked's default: non-space after opening, non-tilde before closing, escape-aware.

### Decisive source
```ts
function trimPartialClosingFences(tokens: readonly Token[]): void {
	// ... recursing into list items and blockquotes ...
	// trims a partial closing fence so an in-flight code block does not
	// VISIBLY SHRINK as each fence character streams in.
	// See https://github.com/earendil-works/pi/issues/5825.
}
```
Styling wraps AFTER word-wrapping (`wrapTextWithAnsi`) so ANSI codes never break width math; heading style-contexts restore themselves after inline token resets; render cache keys on (text, width).

**Flow:** streamed text → parse → trim partial constructs (fences now; unclosed `$…$` held back only if it looks like real math) → wrap to width → apply ANSI styling post-wrap → cache by (text, width).
**Invariant:** Streaming is the NORMAL case: the renderer must tolerate every partially-arrived construct (never render a shrinking block, never swallow prose that merely looks like LaTeX's opening).
**Probe:** `packages/tui/test/markdown.test.ts` (fence + LaTeX streaming cases).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-upstream", query: "trimPartialClosingFences looksLikePendingDollarMath", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt parser-level partial-construct tolerance and post-wrap ANSI styling. Adapt which constructs get trimmed/pended to your grammar. Omit the cache if renders are cheap. Coverage caveat: none.
