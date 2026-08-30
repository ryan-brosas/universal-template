<!-- capsule-v2 -->
# Roving tabindex focus plumbing — how does keyboard state become real DOM focus and back?

**Source:** visx (ui-visx) MIT `master@485c0359664ee8e612992defb16e1f035ed40b23`; Codebase Memory `ext-ui-visx`. **Question:** Who calls `.focus()` when the reducer moves focus, how do points register/unregister, and why is nav disabled above a point threshold?

## Element map + effect-chasing + threshold gate
**Path/Symbol:** `packages/visx-a11y/src/useChartKeyboardNav.ts:useChartKeyboardNav` (:98–238); intent extraction `getKeyboardIntent` (:53–90).
**Signature:** `useChartKeyboardNav(config) => { svgProps, getPointProps(seriesIndex,index), mode, focusedPoint, focusPoint }`.
**Data Shape:** `pointElementsRef = useRef(new Map<string, SVGElement>())` keyed `"${seriesIndex}:${index}"`; `svgProps = {tabIndex?: 0, onKeyDown?, ref}`; `getPointProps` returns `{ref, tabIndex: 0|-1, onFocus, 'data-a11y-focused'?}`.

### Decisive source
```ts
// registration doubles as cleanup — null node DELETES the key
ref: (node) => {
  const key = getPointKey(point);
  if (node) pointElementsRef.current.set(key, node);
  else pointElementsRef.current.delete(key);
},
tabIndex: isFocused ? 0 : -1,

// DOM focus chases state in an effect; datum handed to onPointFocus
useEffect(() => {
  if (!navigationEnabled || state.mode !== 'data' || !focusedPoint) return;
  const focusedElement = pointElementsRef.current.get(getPointKey(focusedPoint));
  focusElement(focusedElement);
  if (datum != null) onPointFocus?.({ seriesIndex, index, datum });
}, [focusedPoint, navigationEnabled, ...]);

// threshold gate: big charts drop BOTH tab stops and key handling
const navigationEnabled =
  keyboardNavEnabled && normalized.pointCount > 0 &&
  normalized.pointCount <= pointDescriptionThreshold;

// exit hands focus BACK to the svg root synchronously after setState
if (intent === 'exit') svgRef.current?.focus();
```

**Flow:** keys → `getKeyboardIntent(event, mode)` (mode-gated: only Enter/Space work in chart mode; Ctrl modifies Home/End) → reducer → effect focuses the mapped element and fires `onPointFocus` with the DATUM → Escape exits and refocuses the SVG. Disabling nav resets state via a dedicated effect.
**Invariant:** exactly ONE point has `tabIndex 0` at any time (roving tabindex); every other point is `-1` but still programmatically focusable. The ref-callback delete-on-null is what prevents stale entries when series shrink — a plain set would leak detached nodes and focus them.
**Probe:** `packages/visx-a11y/test/keyboard.test.tsx :147/:165` (wrap-around flows through rendered DOM); `test/index.test.tsx`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-visx", query: "useChartKeyboardNav getKeyboardIntent", limit: 10, fields: ["signature", "name", "file"] });
// resolves packages/visx-a11y/src/useChartKeyboardNav.ts :53-90
```

## Verdict
Adopt the roving-tabindex pattern (Map registry + delete-on-null + effect-driven focus + exit-refocus) for any custom widget; adapt the threshold default (150) to your data density policy; omit visx prop-type surface.
