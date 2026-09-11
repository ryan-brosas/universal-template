<!-- capsule-v2 -->
# @theme ingestion — how is `@theme` CSS folded into one output `:root, :host` rule while keyframes survive hoisting?

**Source:** tailwindcss MIT `main@90f8ff41c8e2a4d17bc76921e23e9d672123da76`; Codebase Memory `tailwindcss`. **Question:** Where do theme variables get emitted in the output, what happens to extra `@theme` blocks, and how do `@media theme(reference)`/`prefix(x)` imports work?

## parseCss @theme branch
**Path/Symbol:** `packages/tailwindcss/src/index.ts:546-600` (`@theme` walk branch), `:456-544` (`@media` param rewriting), `:654-675` (final theme-variable emission).
**Signature:** inside `parseCss(input, opts)` AST walk; `parseThemeOptions(node.params)` splits flags like `inline`, `reference`, `static`, `default`, `prefix(x)`.
**Data Shape:** consumes at-rule nodes; produces `Theme` entries, a single `firstThemeRule = styleRule(':root, :host', [])`, and hoisted keyframes wrapped as `context({theme:true}, [atRoot([keyframes])])`.

### Decisive source
```ts
// Record all custom properties in the `@theme` declaration
walk(node.nodes, (child) => {
  if (child.kind === 'at-rule' && child.name === '@keyframes') {
    theme.addKeyframes(child)
    return WalkAction.Skip
  }
  if (child.kind === 'comment') return
  if (child.kind === 'declaration' && child.property.startsWith('--')) {
    theme.add(unescape(child.property), child.value ?? '', themeOptions, child.src)
    return
  }
  throw new Error(`\`@theme\` blocks must only contain custom properties or \`@keyframes\`.\n\n${snippet}`)
})
if (!firstThemeRule) {
  firstThemeRule = styleRule(':root, :host', [])
  firstThemeRule.src = node.src
  return WalkAction.ReplaceSkip(firstThemeRule)
} else {
  return WalkAction.ReplaceSkip([])
}
```

**Flow:** every `@theme` block is deleted from the tree; the *first* one is replaced in place by the `:root, :host` output rule that later receives all emitted variables plus collected `@keyframes` (wrapped in `atRoot` so an eventual `@reference` cannot cut them out). Non-custom-property children abort compilation with a pointer-decorated snippet of the offending node. `@import "tailwindcss" theme(reference)`/`prefix(ident)` arrive pre-rewritten as `@media theme(reference)`/`@media prefix(…)` wrappers whose params are appended onto each inner `@theme` block; `important` and bare `reference` media params set compiler-wide state.
**Invariant:** Theme emission position == first `@theme` position; variable output honors per-entry options (REFERENCE entries skipped via `value.options & ThemeOptions.REFERENCE` check before emitting declarations). The hard error on foreign children keeps Theme a pure custom-property store — no selector leakage.
**Probe:** `packages/tailwindcss/src/index.test.ts:1656` "`@keyframes` in `@theme` are hoisted", :2708 "wrapping `@theme` with `@media reference` behaves like `@theme reference` to support `@import` statements", :2788 "`@media theme(reference)` can only contain `@theme` rules", :5541+ layer-position errors.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "tailwindcss", query: "parseCss theme keyframes firstThemeRule reference prefix media important", filePattern: "packages/tailwindcss/src/*", limit: 10, fields: ["lines"] });
```
Observed hit: `parseCss … src/index.ts 142-712` alongside `theme.Theme.addKeyframes`/`getKeyframes`.

## Verdict
Adopt fold-all-blocks-into-one-store + emit-once-at-first-position, keyframes collection with atRoot wrapping, and fail-loud content validation. Adapt the media-param rewriting if your import resolver handles options differently. Omit Tailwind's default-theme import chain (`@import "tailwindcss"` → `theme.css`) when porting only the mechanism.
