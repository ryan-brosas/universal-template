<!-- capsule-v2 -->
# Wrapper-sandwich compiler — how do I run Tailwind v4's compile() as a library and extract only my own emitted CSS?

**Source:** daisyUI MIT `master@c6e1800bc15ab0287b8c2b802c126ccee6361beb`; Codebase Memory `ui-daisyui`. **Question:** How can authored component CSS (with `@apply`, theme vars, `@property`) be compiled through Tailwind while retrieving exactly the payload CSS — no Tailwind preflight, no theme dump?

## Sentinel layers + brace-index extraction
**Path/Symbol:** `packages/daisyui/functions/compileAndExtractStyles.js:5-54` (`loadThemes`, `compileAndExtractStyles`); consumers `cssToJs.js:29-57` and `cleanCss.js:1-24`.
**Signature:** `async compileAndExtractStyles(styleContent, defaultTheme, theme) → Promise<string>`; `async loadThemes() → { defaultTheme, theme }`.
**Data Shape:** input is authored CSS text plus two theme stylesheets (Tailwind's own `theme.css` and daisyUI's `variables.css`). Output is the compiled payload as a string. Failure shape: two typed errors — `"Failed to find wrapper layers in compiled content"` (either sentinel missing) and `"Invalid wrapper structure in compiled content"` (brace indices inverted).

### Decisive source
```js
const compiledContent = (
  await compile(`
    @layer theme{${defaultTheme}${theme}}
    @layer wrapperStart{${styleContent}}
    @layer wrapperEnd
  `, {
    polyfills: 1, // AtProperty only, excludes ColorMix
  })
).build([])

const startIndex = compiledContent.indexOf("@layer wrapperStart")
const endIndex = compiledContent.indexOf("@layer wrapperEnd")
if (startIndex === -1 || endIndex === -1) throw new Error("Failed to find wrapper layers in compiled content")
const openingBraceIndex = compiledContent.indexOf("{", startIndex)
const closingBraceIndex = compiledContent.lastIndexOf("}", endIndex)
...
return compiledContent.substring(openingBraceIndex + 1, closingBraceIndex).trim()
```

**Flow:** payload is embedded between uniquely-named sentinel layers alongside the theme layer so Tailwind resolves every `@apply`/var reference during compilation → `.build([])` with an empty candidate list emits utilities for nothing but still expands the payload → the slice between `wrapperStart{`'s first brace and the last `}` before `wrapperEnd` is exactly the compiled payload → downstream, `cssToJs` continues clean → postcss parse → `postcssJs.objectify` → camelCase→kebab key walk → `replaceApplyTrueWithEmptyObject` → JSON; `cleanCss` first normalizes empty fallbacks (`var(--x,) → var(--x)`), drops `--spacing/--width*` vars when a literal fallback exists, and rewrites `var(--spacing)` to the hardcoded `0.25rem`.
**Invariant:** polyfills are deliberately `AtProperty`-only (numeric enum 1) so `color-mix()` stays native in output; extraction must validate both sentinels exist and braces are ordered before slicing — a missing marker is a hard error, never silent truncation.
**Probe:** no dedicated unit test file exists upstream for this module (coverage caveat recorded); behavior is exercised indirectly by the build pipeline. Deterministic anchors: source lines 16–53 read at pin; `check_index_coverage` = no_recorded_issue.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ui-daisyui", query: "compileAndExtractStyles wrapperStart loadThemes", limit: 10 });
```
Executed this pass: entry-point rows `compileAndExtractStyles.compileAndExtractStyles` / `.loadThemes` surfaced in `get_architecture`; full-file reads of all three modules confirmed the flow above.

## Verdict
Adopt the sentinel-layer sandwich and typed extraction errors as a pure contract for using Tailwind (or any compiler that reorders/emits layers) as an embeddable CSS engine. Adapt which polyfills you enable and where themes come from. Omit daisyUI's `0.25rem` spacing rewrite and its exact theme file locations unless your design system shares them.
