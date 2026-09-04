<!-- capsule-v2 -->
# calculateActiveIndex — how do arrow keys skip disabled items and what do they return when nothing is focusable?

**Source:** Headless UI MIT `main@eea57cf46fd6767ed1059012f7073b88eb159fba`; Codebase Memory `ext-ui-headlessui`. **Question:** What are the six navigation actions' exact failure semantics (null vs current) so porters don't invent loops?

## calculateActiveIndex / Focus
**Path/Symbol:** `packages/@headlessui-react/src/utils/calculate-active-index.ts:5-95`.
**Signature:** `calculateActiveIndex<T>(action: { focus: Focus.Specific; id } | { focus: Exclude<Focus, Focus.Specific> }, resolvers: { resolveItems(): T[]; resolveActiveIndex(): number | null; resolveId(item, idx, items): string; resolveDisabled(item, idx, items): boolean }): number | null`.
**Data Shape:** pure function; NO DOM access — resolvers abstract the item store; `resolveActiveIndex()` returning null is distinct from 0.

### Decisive source
```ts
let activeIndex = currentActiveIndex ?? -1        // null => -1 sentinel
switch (action.focus) {
  case Focus.First:
    for (let i = 0; i < items.length; ++i) if (!resolvers.resolveDisabled(items[i], i, items)) return i
    return currentActiveIndex                      // ALL disabled: keep current (no wrap!)
  case Focus.Previous:
    if (activeIndex === -1) activeIndex = items.length   // nothing active: start from END
    for (let i = activeIndex - 1; i >= 0; --i) ...
    return currentActiveIndex
  case Focus.Next:
    for (let i = activeIndex + 1; i < items.length; ++i) ...
    return currentActiveIndex
  case Focus.Specific:
    for (...) if (resolvers.resolveId(...) === action.id) return i
    return currentActiveIndex
  case Focus.Nothing: return null                  // explicit CLEAR returns null, not current
}
```

**Flow:** First/Last scan outward for first enabled; Previous/Next scan one direction WITHOUT wrapping and fall back to currentActiveIndex on exhaustion; Specific matches by resolver id; Nothing clears to null. The all-disabled case therefore NEVER moves selection and never throws — callers distinguish "stayed" (number) from "cleared" (null).
**Invariant:** Previous-from-nothing seeds `items.length` (not length-1) so the loop's first check IS the last item; Next/Previous deliberately do NOT wrap — wrapping is a caller decision (Focus.WrapAround exists only in the DOM-level focusIn, a DIFFERENT enum with the same name!); resolvers receive (item, index, items) triads.
**Probe:** live `/tmp/hui-pass1-probe/probe-index-store.mjs`: first-skips-disabled=0, next-skips=2, next-from-keeps-current=3, prev-from-null-starts-at-end=3, specific=2, nothing=null, all-disabled keeps current. Direct tests: listbox.test.tsx Keyboard suites pin every arrow path incl. disabled skipping.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-headlessui", query: "calculateActiveIndex", name_pattern: "^calculateActiveIndex$", limit: 5 });
```

## Verdict
Adopt verbatim including the two-enums-with-one-name trap (`utils/calculate-active-index.Focus` {First..Nothing} vs `utils/focus-management.Focus` bitmask — importing the wrong one compiles but misbehaves); adapt resolver shapes to your state; omit assertNever only if your switch is exhaustive-checked.
