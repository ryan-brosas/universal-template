<!-- capsule-v2 -->
# Theme injection ladder — how do string-flagged theme options become exact base-layer CSS selectors without duplicate applications?

**Source:** daisyUI MIT `master@c6e1800bc15ab0287b8c2b802c126ccee6361beb`; Codebase Memory `ui-daisyui`. **Question:** How do I turn `themes: ["light --default", "dark --prefersdark"]`-style options into default/prefers-dark/named-theme selectors that a `[data-theme]` attribute or a checked radio can override?

## Flag-parsed option grammar → selector construction
**Path/Symbol:** `packages/daisyui/functions/pluginOptionsHandler.js:22-95` (`applyTheme` + three-pass application).
**Signature:** `pluginOptionsHandler(options, addBase, themesObject, packageVersion) → { include?, exclude?, prefix }`; inner `applyTheme(themeName, flags[])`.
**Data Shape:** `themesObject: {themeName → {cssPropertyOrVar: value}}` (selectorless custom-property blocks; see `src/themes/light.css:1-29` — oklch color tokens plus `--radius-*`, `--size-*`, `--border`, `--depth`, `--noise`). Each option string is `"name [--default] [--prefersdark]"`; `themes: "all"` applies light as default, dark as prefers-dark, then every theme in `themeOrder`.

### Decisive source
```js
let selector = `${root}:has(input.${themeControllerClass}[value=${themeName}]:checked),[data-theme=${themeName}]`
if (flags.includes("--default")) {
  selector = `:where(${root}),${selector}`
}
addBase({ [selector]: theme })

if (flags.includes("--prefersdark")) {
  const darkSelector =
    root === ":root" ? ":root:not([data-theme])" : `${root}:not([data-theme])`
  addBase({ "@media (prefers-color-scheme: dark)": { [darkSelector]: theme } })
}

// single theme with --default flag: skip the other applications
if (themeArray.length === 1 && themeArray[0].includes("--default")) {
  const [themeName, ...flags] = themeArray[0].split(" ")
  applyTheme(themeName, flags)
  return { include, exclude, prefix }
}
```

**Flow:** defaults are `["light --default", "dark --prefersdark"]` → for each option the name and flags split on spaces → named themes emit `root:has(input.theme-controller[value=name]:checked), [data-theme=name]` so either a checkbox/radio toggle or a data attribute switches tokens at zero JS cost → `--default` prepends `:where(root)` giving an unconditional but zero-specificity fallback → `--prefersdark` emits the same token block under `@media (prefers-color-scheme: dark)` scoped to `root:not([data-theme])` so an explicit attribute beats OS preference → application order is default-themes first, prefers-dark second, remaining named themes last.
**Invariant:** a single-theme `["x --default"]` config must call `addBase` exactly once (early return prevents a second identical application); the theme-controller class name carries the prefix; the token block itself stays selectorless — all selection logic lives in the generated selector.
**Probe:** `packages/daisyui/functions/pluginOptionsHandler.test.js` asserts byte-exact selectors (`":where(:root),:root:has(input.theme-controller[value=light]:checked),[data-theme=light]"`) and call counts (4 for defaults incl. both dark emissions, 1 for single theme); `bun test functions/pluginOptionsHandler.test.js` GREEN at pin.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ui-daisyui", query: "applyTheme pluginOptionsHandler theme selector", limit: 10 });
```
Executed this pass via BM25 search over `packages/daisyui/*` returning `plugin.withOptions/optionsFunction` and full-file reads of handler + test.

## Verdict
Adopt the selector algebra — `:where()` default, `[data-theme]` switch, `:has(input:checked)` controller, `:not([data-theme])`-gated prefers-dark media — as a pure contract. Adapt the option grammar, root option, and theme vocabulary. Omit daisyUI's specific token names unless porting its palette; note the banner log is gated by a closure `firstRun` flag plus `logs !== false` so repeated builds print once.
