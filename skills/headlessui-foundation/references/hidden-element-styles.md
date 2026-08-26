<!-- capsule-v2 -->
# Hidden element styles — how does one component produce focusable guards, screen-reader-only text, and fully hidden inputs?

**Source:** Headless UI MIT `main@eea57cf46fd6767ed1059012f7073b88eb159fba`; Codebase Memory `ext-ui-headlessui`. **Question:** What are the three HiddenFeatures style/aria combinations and where is each used?

## Hidden / HiddenFeatures
**Path/Symbol:** `packages/@headlessui-react/src/internal/hidden.tsx:8-75`.
**Signature:** `enum HiddenFeatures { None = 1<<0, Focusable = 1<<1, Hidden = 1<<2 }`; `Hidden({ features? = None, ...props })` renders via useRender (polymorphic, default span).
**Data Shape:** fixed inline style block; `aria-hidden` forced TRUE when Focusable; `display:none` added only when Hidden AND NOT Focusable.

### Decisive source
```ts
let ourProps = {
  ref,
  'aria-hidden': (features & Focusable) === Focusable ? true : theirProps['aria-hidden'] ?? undefined,
  hidden:      (features & Hidden)    === Hidden ? true : undefined,
  style: {
    position: 'fixed', top: 1, left: 1, width: 1, height: 0,
    padding: 0, margin: -1, overflow: 'hidden',
    clip: 'rect(0, 0, 0, 0)', whiteSpace: 'nowrap', borderWidth: '0',
    ...((features & Hidden) && !(features & Focusable) && { display: 'none' }),
  },
}
```

**Flow:** default (None): visually-hidden but screen-reader-visible (classic sr-only block). +Focusable: same geometry, aria-hidden=true, REMAINS in tab order — this is the focus-trap guard button and FocusSentinel. +Hidden: display:none for form-field markers and probe elements that must not affect layout OR a11y tree.
**Invariant:** the clip-rect block must stay a GROUP — dropping any single property (e.g. margin:-1) resurrects scrollbars or focus rings; Focusable+Hidden together means aria-hidden + tabbable + display:none which would be unreachable, hence the `&& !Focusable` guard.
**Probe:** deterministic checks executed against the style matrix. Direct tests: portal.test.tsx/form suites assert rendered hidden inputs; focus-trap tests exercise guard buttons (as="button" type="button").
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-headlessui", query: "HiddenFeatures VisuallyHidden", name_pattern: "^HiddenFeatures$", limit: 5 });
```

## Verdict
Adopt the feature matrix verbatim; adapt the tag via your render-prop system; omit None-mode if you have a native sr-only class — but keep the Focusable variant exactly, it's what makes trap guards work without being visible to screen readers.
