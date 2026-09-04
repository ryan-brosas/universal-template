<!-- capsule-v2 -->
# Focusable enumeration — which elements count as focusable, in what order, and when is focus "restored"?

**Source:** Headless UI MIT `main@eea57cf46fd6767ed1059012f7073b88eb159fba`; Codebase Memory `ext-ui-headlessui`. **Question:** How does Headless UI enumerate focusable elements (selector + ordering) and decide that a previously focused element must be re-focused?

## focusableSelector / getFocusableElements / isFocusableElement / restoreFocusIfNecessary
**Path/Symbol:** `packages/@headlessui-react/src/utils/focus-management.ts:9-45` (selectors), `:93-109` (`getFocusableElements`, `getAutoFocusableElements`), `:111-154` (`isFocusableElement`, `restoreFocusIfNecessary`).
**Signature:** `getFocusableElements(container?: QuerySelectorAll | null): HTMLElement[]`; `isFocusableElement(element, mode = Strict): boolean`; `restoreFocusIfNecessary(element: HTMLElement | null): void`.
**Data Shape:** selector string built once at module load; NODE_ENV==='test' appends `:not([style*='display: none'])` per clause (JSDOM lets hidden elements be activeElement).

### Decisive source
```ts
export let focusableSelector = [
  '[contentEditable=true]', '[tabindex]', 'a[href]', 'area[href]',
  'button:not([disabled])', 'iframe', 'input:not([disabled])',
  'select:not([disabled])', 'details>summary', 'textarea:not([disabled])',
].map((s) => `${s}:not([tabindex='-1'])`).join(',')

return Array.from(container.querySelectorAll<HTMLElement>(focusableSelector)).sort(
  // We want to move `tabIndex={0}` to the end of the list, this is what the browser does as well.
  (a, z) => Math.sign((a.tabIndex || Number.MAX_SAFE_INTEGER) - (z.tabIndex || Number.MAX_SAFE_INTEGER))
)

export function restoreFocusIfNecessary(element) {
  disposables().nextFrame(() => {
    let activeElement = getActiveElement(element)
    if (activeElement && DOM.isHTMLorSVGElement(activeElement) &&
        !isFocusableElement(activeElement, FocusableMode.Strict)) focusElement(element)
  })
}
```

**Flow:** querySelectorAll over ONE flat selector → stable sort pushing tabIndex 0 (falsy!) to MAX_SAFE_INTEGER so explicit positive tabindices go first and ordinary elements follow document order (Array.sort is stable per spec) → Loose mode walks parentElement chain testing each node against the same selector (clicking a span inside a button counts as the button). Restore waits TWO animation frames then only restores when the current active element fails STRICT matching.
**Invariant:** `a.tabIndex || Number.MAX_SAFE_INTEGER` treats tabIndex=0 AND missing tabIndex identically (end of positive group, preserving DOM order); `-1` is excluded by the selector itself, not the sort; body always fails isFocusableElement.
**Probe:** direct test `src/utils/get-text-value.test.ts` sibling coverage plus dialog tests exercising tab order; deterministic probe: selector excludes `[tabindex='-1']`, sort comparator returns 0 for equal keys keeping DOM order. Live check executed via probe-focusin battery using ordered arrays.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-headlessui", query: "getFocusableElements", name_pattern: "^getFocusableElements$", limit: 5 });
```

## Verdict
Adopt the selector list and falsy-tabIndex sort verbatim (this IS browser tab order); adapt the test-env display-none clauses to your test runner's quirks; omit `details>summary` handling if your browser matrix predates it. Caveat: no dedicated unit test file — behavior pinned transitively through dialog.test.tsx keyboard suites.
