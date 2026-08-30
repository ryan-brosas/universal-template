<!-- capsule-v2 -->
# Theme resolve var/inline — when does theme resolution emit `var(--key)` versus an inline value, and what does REFERENCE mode imply?

**Source:** tailwindcss MIT `main@90f8ff41c8e2a4d17bc76921e23e9d672123da76`; Codebase Memory `tailwindcss`. **Question:** How does one resolution path serve both "emit CSS variables in `:root` and reference them" and "inline literal values (email/CSS-modules contexts)", plus `@theme reference` fallbacks?

## Theme.resolve / #var / markUsedVariable
**Path/Symbol:** `packages/tailwindcss/src/theme.ts:168-235` (`#resolveKey`, `#var`, `markUsedVariable`, `resolve`), `:245-274` (`resolveWith` for nested keys like `--font-size-sm--line-height`).
**Signature:** `resolve(candidateValue: string | null, themeKeys: ThemeKey[], options = NONE): string | null`; `markUsedVariable(themeKey): boolean`.
**Data Shape:** theme key candidates tried in order (`namespace`, then `namespace-value`), dot-in-candidate falls back to underscore-registered keys; result is either the raw value or a `var()` string.

### Decisive source
```ts
// Since @theme blocks in reference mode do not emit the CSS variables, we can
// not assume that the values will eventually be set up in the browser ...
let fallback = null
if (value.options & ThemeOptions.REFERENCE) {
  fallback = value.value
}
return `var(${escape(this.prefixKey(themeKey))}${fallback ? `, ${fallback}` : ''})`
...
if ((options | value.options) & ThemeOptions.INLINE) {
  return value.value
}
return this.#var(themeKey)
```

**Flow:** `#resolveKey` walks candidate namespaces, tolerating dot→underscore aliasing and rejecting protected/ignored keys → if INLINE is requested by caller *or* set on the entry, return the literal value; otherwise emit an escaped, prefix-aware `var(--key)` with an inline fallback only under REFERENCE (because reference blocks never emit the variable definition). `markUsedVariable` flips the USED bit and returns whether it was the first use — that boolean is what lets `compileAst.build()` skip rebuilds when nothing new became used.
**Invariant:** Resolution never mutates values except the USED bit; emitted variable names go through both `escape` and `prefixKey` so prefixed themes (`@theme prefix(tw)`) still resolve un-prefixed internal lookups. `resolveValue` bypasses var-emission entirely for callers needing raw data (IntelliSense).
**Probe:** `packages/tailwindcss/src/index.test.ts:2534` "theme values added as reference are not included in the output as variables but emit fallback values", :2809/:2840 (inline values not wrapped in `var(…)`), :3255 "only emits theme variables that are used outside of being defined by another variable".

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "tailwindcss", query: "theme resolve INLINE REFERENCE var fallback markUsedVariable used", filePattern: "packages/tailwindcss/src/*", limit: 10, fields: ["lines"] });
```
Observed top hits: `theme.Theme.markUsedVariable … theme.ts 210-217`, `theme.Theme.#var … theme.ts 193-208`, `theme.Theme.resolve … theme.ts 219-235`.

## Verdict
Adopt the single-resolution-path design with option bits deciding var vs inline, the REFERENCE-only fallback emission, and first-use booleans feeding incremental rebuild gates. Adapt the escaping/prefix rules to your variable naming scheme. Omit the compat-layer `resolveThemeValue` shims (`compat/apply-config-to-theme`) unless porting JS-config back-compat.
