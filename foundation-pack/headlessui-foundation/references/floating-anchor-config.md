<!-- capsule-v2 -->
# Floating anchor config — how do `anchor` props resolve CSS variables to px values and keep panels positioned via floating-ui?

**Source:** Headless UI MIT `main@eea57cf46fd6767ed1059012f7073b88eb159fba`; Codebase Memory `ext-ui-headlessui`. **Question:** What is the CSS-variable→pixel resolution trick (probe element) and the polling watcher fallback?

## useResolvePxValue / resolveCSSVariablePxValue / useResolvedConfig
**Path/Symbol:** `packages/@headlessui-react/src/internal/floating.tsx:437-591` (resolution), `:409-436` (`useResolvedConfig`); middleware assembly flip/shift/offset/size/inner + autoUpdate.
**Signature:** `useResolvePxValue(input?: string | number, element?: HTMLElement | null, defaultValue?): number | undefined`; `resolveCSSVariablePxValue(input: string, element: HTMLElement): number`.
**Data Shape:** anchor config `{ gap|offset|padding: number | string }` where strings are CSS values incl. `var(--anchor-gap, 0)`; defaults read the same CSS custom properties.

### Decisive source
```ts
function resolveCSSVariablePxValue(input, element) {
  // Let the BROWSER compute rem/vh/calc/fallback chains:
  let tmpEl = document.createElement('div')
  element.appendChild(tmpEl)
  tmpEl.style.setProperty('margin-top', '0px', 'important')   // 0 baseline (margin can go negative)
  tmpEl.style.setProperty('margin-top', input, 'important')   // invalid => keeps previous
  let pxValue = parseFloat(window.getComputedStyle(tmpEl).marginTop) || 0
  element.removeChild(tmpEl)
  return pxValue
}
// change detection WITHOUT ResizeObserver-on-custom-properties support:
let history = variables.map((v) => window.getComputedStyle(element!).getPropertyValue(v))
d.requestAnimationFrame(function check() {
  d.nextFrame(check)                       // continuous rAF loop
  let changed = false
  for (let [idx, variable] of variables.entries()) {
    let value = window.getComputedStyle(element!).getPropertyValue(variable)
    if (history[idx] !== value) { history[idx] = value; changed = true; break }
  }
  if (!changed) return                     // fast path: skip expensive probe
  let newResult = resolveCSSVariablePxValue(value, element)
  if (result !== newResult) { setValue(newResult); result = newResult }
})
```

**Flow:** resolveVariables extracts var names recursively INCLUDING nested fallbacks → immediate compute once per input/element → watcher loop polls raw computed property values each frame and only re-runs the probe-element computation when something changed → resolved numbers feed floating-ui offset/size middleware.
**Invariant:** margin-top (not font-size) is the probe property because it accepts negative px; invalid values fall back silently to the previous valid one — that's why the 0px baseline write precedes the real value; the documented BUG: the probe element inherits the PARENT's cascade so `.parent{--v:1rem} .parent>*{--v:2rem}` resolves 2rem not 1rem.
**Probe:** deterministic ladder checks executed (var-fallback recursion; margin-probe semantics). Direct behavior pinned by combobox/listbox anchor suites (positioned rendering in jsdom is limited — real positioning verified visually upstream).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-headlessui", query: "useResolvePxValue resolveCSSVariablePxValue", name_pattern: "^useResolvePxValue$|^resolveCSSVariablePxValue$", limit: 5 });
```

## Verdict
Adopt the probe-element resolution when your anchor offsets accept arbitrary CSS; adapt the rAF poll to your scheduler but keep the cheap-diff fast path or you'll recompute layout every frame; omit inner/selection middleware if you don't need selection-anchored comboboxes. Heed the inherited-cascade bug note before copying.
