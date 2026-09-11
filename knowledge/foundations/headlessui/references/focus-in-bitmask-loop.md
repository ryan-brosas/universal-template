<!-- capsule-v2 -->
# Focus bitmask loop — how do First/Previous/Next/Last/WrapAround resolve without an index bookkeeping bug?

**Source:** Headless UI MIT `main@eea57cf46fd6767ed1059012f7073b88eb159fba`; Codebase Memory `ext-ui-headlessui`. **Question:** What is the exact algorithm for moving focus among focusable elements so wrap, underflow, and hidden elements behave like the browser?

## focusIn / Focus / FocusResult
**Path/Symbol:** `packages/@headlessui-react/src/utils/focus-management.ts:235-332` (`focusIn`), `:47-82` (`Focus`, `FocusResult`).
**Signature:** `function focusIn(container: HTMLElement | HTMLElement[], focus: Focus, opts?: { sorted?: boolean; relativeTo?: HTMLElement | null; skipElements?: (HTMLElement | Ref)[] }): FocusResult`.
**Data Shape:** `Focus` bits compose with `|` (`First|AutoFocus`); direction is REQUIRED exactly once or `throw new Error('Missing Focus.First...')`; result is one of Error/Overflow/Success/Underflow.

### Decisive source
```ts
let direction = (() => {
  if (focus & (Focus.First | Focus.Next)) return Direction.Next
  if (focus & (Focus.Previous | Focus.Last)) return Direction.Previous
  throw new Error('Missing Focus.First, Focus.Previous, Focus.Next or Focus.Last')
})()
let startIndex = (() => {
  if (focus & Focus.First) return 0
  if (focus & Focus.Previous) return Math.max(0, elements.indexOf(relativeTo)) - 1
  if (focus & Focus.Next) return Math.max(0, elements.indexOf(relativeTo)) + 1
  if (focus & Focus.Last) return elements.length - 1
})()
...
do {
  if (offset >= total || offset + total <= 0) return FocusResult.Error   // infinite-loop guard
  let nextIdx = startIndex + offset
  if (focus & Focus.WrapAround) nextIdx = (nextIdx + total) % total      // modular, never negative
  else { if (nextIdx < 0) return FocusResult.Underflow; if (nextIdx >= total) return FocusResult.Overflow }
  next = elements[nextIdx]
  next?.focus(focusOptions)
  offset += direction
} while (next !== getActiveElement(next))   // retry while element refused focus
```

**Flow:** derive direction+startIndex from bits → do/while attempts `element.focus()` and advances by ±1 until `activeElement === attempted` → on success (and only for Next/Previous moves) text inputs get `.select()` to mimic browser Tab behavior → return Success. Elements that silently refuse focus (display:none in real browsers) are skipped by the loop itself.
**Invariant:** WrapAround uses `(idx+total)%total` so Previous-from-first wraps to last; WITHOUT the bit you must return Underflow/Overflow instead of throwing; the loop can consume at most `total` steps before the guard returns Error. `relativeTo` defaults to the CURRENT activeElement — callers that pass `relativeTo` explicitly override where Next/Previous start.
**Probe:** live port `/tmp/hui-pass1-probe/probe-focusin.mjs`: first→a, next→b, prev→a, last→c, wrap-next-from-last→a, prev-no-wrap→Underflow, next-past-last→Overflow (all Success/edge results match source semantics). Direct test: `packages/@headlessui-react/src/components/dialog/dialog.test.tsx:836-933` pins tab-around and cannot-escape-with-1-focusable behavior.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-headlessui", query: "focusIn", name_pattern: "^focusIn$", limit: 5 });
```

## Verdict
Adopt the bit vocabulary, direction-derivation throw, modular wraparound, and try-until-activeElement loop verbatim; adapt the selectable-element `.select()` carve-out if your host has no text inputs; omit the test-env selector variant (JSDOM-only). Note the Vue twin (`@headlessui-vue/src/utils/focus-management.ts:190-274`) is contract-identical.
