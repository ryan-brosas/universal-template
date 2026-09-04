<!-- capsule-v2 -->
# Leading-edge debounce with ignore-dims — how does ParentSize avoid resize loops while staying responsive on first paint?

**Source:** visx (ui-visx) MIT `master@485c0359664ee8e612992defb16e1f035ed40b23`; Codebase Memory `ext-ui-visx`. **Question:** Why does useParentSize need a CUSTOM leading-call debounce, and what is the ignoreDimensions bail rule?

## rAF → leading debounce → all-changed-keys bail
**Path/Symbol:** `packages/visx-responsive/src/hooks/useParentSize.ts:useParentSize` (:38–108); debounce impl `utils/debounce.ts` (:18–59).
**Signature:** `debounce(func, wait, {leading}) => fn & {cancel()}`; `useParentSize({initialSize?, debounceTime=300, ignoreDimensions=[], enableDebounceLeadingCall=true, resizeObserverPolyfill?})`.
**Data Shape:** `ParentSizeState = {width,height,top,left}`; RO entry `contentRect` feeds it directly.

### Decisive source
```ts
// custom debounce: leading fires NOW, trailing only if more calls came during wait
if (leading && timeoutId === undefined) { func.apply(this, args); pendingArgs = null; }
else { pendingArgs = args; pendingContext = this; }
clearTimeout(timeoutId);
timeoutId = setTimeout(() => { timeoutId = undefined;
  if (pendingArgs !== null) func.apply(pendingContext, pendingArgs); }, wait);
```
```ts
// bail ONLY when every changed key is ignored (partial overlap still updates!)
const keysWithChanges = stateKeys.filter((key) => existing[key] !== incoming[key]);
const shouldBail = keysWithChanges.every((key) => normalized.includes(key));
return shouldBail ? existing : incoming;
```

**Flow:** ResizeObserver → `requestAnimationFrame` (coalesce per frame) → debounced resize → setState unless ignored. Leading call makes the FIRST measurement apply instantly (no blank chart for debounceTime ms); trailing coalesces the burst that follows. Cleanup cancels rAF + observer + pending debounce on unmount/node change.
**Invariant:** the ignore check compares CHANGED KEYS ONLY: ignoring `['width']` still lets a height-only change through (`keysWithChanges=['height']`, not every key ignored). lodash's default trailing debounce would delay the initial render — the leading variant exists precisely to kill that blank window.
**Probe:** `packages/visx-responsive/test/useParentSize.test.tsx` (MockResizeObserver-driven timing cases); `test/ParentSize.test.tsx`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-visx", query: "useParentSize ResizeObserver contentRect", limit: 10, fields: ["signature", "name", "file"] });
await mcp.codebase_memory.search_graph({ project: "ext-ui-visx", query: "debounce pendingArgs leading", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt debounce + bail-rule verbatim (host-agnostic); adapt debounceTime defaults and polyfill injection; omit HOC wrappers (withParentSize etc.).
