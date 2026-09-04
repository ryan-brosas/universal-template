<!-- capsule-v2 -->
# Focus trap guards — how do hidden sentinel buttons, blur redirection, and a microtask focus ladder keep Tab inside the Dialog?

**Source:** Headless UI MIT `main@eea57cf46fd6767ed1059012f7073b88eb159fba`; Codebase Memory `ext-ui-headlessui`. **Question:** What is the full FocusTrap mechanism — guards, features bitmask, initial-focus ladder, and restore-from-history?

## FocusTrap / FocusTrapFeatures / useRestoreElement
**Path/Symbol:** `packages/@headlessui-react/src/components/focus-trap/focus-trap.tsx:53-247` (component+guards), `:251-303` (`useRestoreElement`, `useRestoreFocus`), `:305-410` (`useInitialFocus`), `:412-468` (`useFocusLock`); history source `utils/active-element-history.ts:5-40`.
**Signature:** `features = InitialFocus | TabLock | FocusLock | RestoreFocus` (bits 1<<0..1<<4 incl. AutoFocus); `containers?: (() => Iterable<Element>) | RefObject<Set<Ref>>`.
**Data Shape:** global `history: HTMLElement[]` capped at 10, fed by window+body capture listeners for click/mousedown/focus, resolving to closest focusable ancestor.

### Decisive source
```ts
// TabLock: two Hidden Focusable buttons flank the content; onFocus re-injects:
[TabDirection.Forwards]: () => focusIn(el, Focus.First, { skipElements: [e.relatedTarget, initialFocusFallback] }),
[TabDirection.Backwards]: () => focusIn(el, Focus.Last, { skipElements: [e.relatedTarget, initialFocusFallback] }),

// FocusLock onBlur redirect:
if (recentlyUsedTabKey.current) {
  focusIn(container.current,
    match(direction.current, { [Forwards]: () => Focus.Next, [Backwards]: () => Focus.Previous }) | Focus.WrapAround,
    { relativeTo: e.target })
} else if (DOM.isHTMLorSVGElement(e.target)) {
  focusElement(e.target)     // programmatic/click escape: snap BACK to origin
}

// InitialFocus ladder (inside microTask — prevents transition-cancel + page scroll):
if (initialFocus?.current) focusElement(initialFocus.current)
else if (features & AutoFocus && focusIn(c, Focus.First | Focus.AutoFocus) !== Error) return
else if (focusIn(c, Focus.First) !== Error) return
else if (initialFocusFallback?.current) focusElement(initialFocusFallback.current)
else console.warn('There are no focusable elements inside the <FocusTrap />')

// RestoreFocus: snapshot of GLOBAL click history at enable time; replay last connected entry:
return localHistory.current.find((x) => x != null && x.isConnected) ?? null
```

**Flow:** Tab keydown marks `recentlyUsedTabKey` (cleared on next rAF) → guard-button focus events run handleFocus which re-enters via First/Last skipping the relatedTarget so focus lands INSIDE → any blur whose relatedTarget escapes all containers is redirected (keyboard ⇒ Next/Previous with WrapAround; pointer/programmatic ⇒ refocus origin; guard elements marked `data-headlessui-focus-guard=true` are exempt). Restore waits for unmount/disable then focuses first still-connected history element ONLY if body is active.
**Invariant:** initial focus MUST be deferred a microTask (focusing immediately cancels running transitions AND scroll-jumps because the portal sits at body end); skipElements accepts raw elements AND refs ('current' in skipElement branch); Dialog passes its own container as initialFocusFallback but EXCLUDES it from tabbing via skip.
**Probe:** deterministic checks: skip-filter handles refs vs elements; direction match maps to Next/Previous|WrapAround. Direct tests: `dialog.test.tsx:719-982` Keyboard suites pin tab-around-with-initialFocus and cannot-escape-forwards/backwards with one focusable; focus-trap.test.tsx covers the standalone component.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-headlessui", query: "FocusTrapFeatures", name_pattern: "^FocusTrapFeatures$", limit: 5 });
```

## Verdict
Adopt guard-button flanking, the two-mode blur redirect, and the microtask initial-focus ladder verbatim; adapt the history module if your host tracks focus differently (any ring buffer of recently-focused connected elements works); omit AutoFocus bit if you don't use data-autofocus. Caveat: restore replays a SNAPSHOT taken when RestoreFocus enabled — later clicks before close are intentionally ignored.
