<!-- capsule-v2 -->
# Chart a11y composition hook — how do aria props, keyboard nav, announcer, and data table compose into ONE hook result?

**Source:** visx (ui-visx) MIT `master@485c0359664ee8e612992defb16e1f035ed40b23`; Codebase Memory `ext-ui-visx`. **Question:** How are two `svgProps` sources and two `getPointProps` layers merged without one clobbering the other, and why are components returned FROM the hook?

## Merge order = keyboard wins; components as stable callbacks
**Path/Symbol:** `packages/visx-a11y/src/useChartA11y.tsx:useChartA11y` (:57–146).
**Signature:** `useChartA11y<Datum>(config): UseChartA11yResult<Datum>` — `{id, ids, svgProps, getSeriesProps, getPointProps, descriptionId, description, DataTable, Announcer, announce, mode, focusedPoint}`.
**Data Shape:** id resolution ladder `config.id ?? '<idPrefix|visx-a11y>-<sanitized useId()>'` where sanitize strips `[^\w-]` falling back to `'chart'`.

### Decisive source
```ts
const svgProps = useMemo(() => ({
  ...ariaProps.svg,       // role/aria-label/aria-describedby first...
  ...keyboardSvgProps,    // ...onKeyDown/tabIndex/ref OVERRIDE — but never collide in practice
}), [ariaProps.svg, keyboardSvgProps]);

const getPointProps = useCallback((seriesIndex, index) => ({
  ...pointProps,                        // aria role/label per point (may be undefined above threshold)
  ...getKeyboardPointProps(seriesIndex, index), // ref/tabIndex/onFocus ALWAYS win
}), [ariaProps.points, getKeyboardPointProps]);
```

**Flow:** `useId` → stable id → memoized config → aria + description generators → keyboard hook (its `onKeyboardHelp` is wired to `setAnnouncement`, feeding the Announcer) → merged prop factories; `DataTable`/`Announcer` are inline callback components so consumers render them positionally (`{a11y.DataTable}`) with the hook holding all wiring.
**Invariant:** spread ORDER is load-bearing: keyboard props must override aria defaults at the SVG level, and keyboard point props (focus machinery) must override aria point labels' potential undefined. `hookConfig` memoizes on the ORIGINAL config object — an inline literal re-runs all generators every render.
**Probe:** `packages/visx-a11y/test/useChartA11y.test.tsx` (composition); `test/announcer.test.tsx` (live-region rendering).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-visx", query: "useChartA11y announcer announce", limit: 10, fields: ["signature", "name", "file"] });
// resolves packages/visx-a11y/src/useChartA11y.tsx :57-146
```

## Verdict
Adopt merge-order rule + returned-components pattern for any multi-feature widget hook; adapt id prefix/sanitization to host conventions; omit visx type plumbing.
