<!-- capsule-v2 -->
# Responsive variant pipeline — how do I generate static `md:`/`lg:` variants of plain CSS without a JIT runtime?

**Source:** daisyUI MIT `master@c6e1800bc15ab0287b8c2b802c126ccee6361beb`; Codebase Memory `ui-daisyui`. **Question:** Given compiled component CSS, how do I produce one `@media (min-width: …)` block per breakpoint containing breakpoint-prefixed copies of top-level rules — once, with keyframes intact?

## Per-breakpoint recompile with top-level-only renaming
**Path/Symbol:** `packages/daisyui/functions/generateRawStyles.js:11-81` (`transformSelector`, `escapeBreakpointColon`, `extractKeyframes`, `hasRuleAncestor`, `generateResponsiveVariants`).
**Signature:** `async generateResponsiveVariants(css: string) → Promise<string>`; helper `transformSelector(selector, breakpoint)` via `postcss-selector-parser`.
**Data Shape:** input is compiled CSS text; `breakpoints.js` supplies `{sm…2xl → min-width}`. Output = original CSS + per-breakpoint media blocks + hoisted keyframes appended once at the end.

### Decisive source
```js
export function transformSelector(selector, breakpoint) {
  return selectorParser((selectors) => {
    selectors.each((selector) => {
      if (selector.first.type === "class") {
        selector.first.value = `${breakpoint}:${selector.first.value}`
      }
    })
  }).processSync(selector)
}

root.walkRules((rule) => {
  if (!hasRuleAncestor(rule)) {           // only top-level rules
    rule.selector = transformSelector(rule.selector, breakpoint)
  }
})
const escapedCss = escapeBreakpointColon(prefixedCss.css, breakpoint) // \.md: → \.md\:
responsiveStyles += generateMediaQuery(breakpoint, minWidth, escapedCss)
return root.toString() + responsiveStyles + keyframesStyles
```

**Flow:** keyframes are extracted and removed first so they never duplicate inside media queries → for each breakpoint the whole sheet is re-parsed and every *top-level* rule's first class is renamed to `md:name` (nested rules guarded by `hasRuleAncestor`, so `.footer { & > .title }` keeps an unprefixed nested selector) → the generated colon is backslash-escaped so Tailwind reads the class as a variant → each variant copy is wrapped in its min-width media query → base CSS + all media blocks + keyframes are concatenated.
**Invariant:** keyframes appear exactly once in output (`result.match(/@keyframes pulse/g)).toHaveLength(1)` pinned); entry rules through structural at-rules (`@layer`, `@media`, `@supports`) get prefixed while their nested descendants do not (`.md\:card` but never `.md\:&`).
**Probe:** `packages/daisyui/functions/generateRawStyles.test.js:12-78`. Runner caveat recorded honestly: this suite imports postcss, which is absent from the read-only checkout — `bun test` failed with `Cannot find package 'postcss'` (56 other tests across the three dependency-free suites passed). Claims rest on direct source reads plus byte-pinned test expectations, not a live run of this file.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ui-daisyui", query: "generateResponsiveVariants transformSelector escapeBreakpointColon", limit: 10 });
```
Executed this pass: BM25 search returned both symbols in `generateRawStyles.js`; full file read confirmed line ranges; `check_index_coverage` reported no_recorded_issue for the source and test.

## Verdict
Adopt "rename first class of top-level rules per breakpoint + escape colon + wrap in media query + hoist keyframes" as the static-variant contract. Adapt the breakpoint table and naming convention. Omit daisyUI's exclude-list wiring (11 components skip responsive generation) unless porting its exact build.
