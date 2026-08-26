<!-- capsule-v2 -->
# Roving tabindex broker — how does one Tab stop represent a whole widget group through mount/unmount, hydration, RTL, and loop modes?

**Source:** radix-ui/primitives MIT `main@f7ecd5ab16f5e1e820eb5786a1419a98a2d594ae`; Codebase Memory `ext-ui-radix-ui`. **Question:** How do group/item tabIndex values get brokered so exactly one item is tabbable, including SSR-hydration timing and direction-aware looping?

## Connected graph-selected seam
**Path/Symbol:** `packages/react/roving-focus/src/roving-focus-group.tsx:RovingFocusGroupImpl` (:110-208), dual-effect item registration (:263-282), entry-focus choreography (:179-203), key map + intent resolver (:348-375), item keydown ladder (:304-335).
**Signature:** `<RovingFocusGroup orientation? dir? loop? currentTabStopId? onEntryFocus? preventScrollOnEntryFocus?>` + `<RovingFocusGroupItem focusable=true active=false tabStopId?>`; group `tabIndex={isTabbingBackOut || focusableItemsCount === 0 ? -1 : 0}`, item `tabIndex={isCurrentTabStop ? 0 : -1}`.
**Data Shape:** collection items carry `{id, focusable, active}`; focusableItemsCount state drives group tabbability; ENTRY_FOCUS custom event cancelable.

### Decisive source
```ts
// Post-hydration: layout effect so the count (and therefore group tabIndex)
// resolves BEFORE paint — otherwise FocusScope reads stale tabIndex={-1} and
// skips the group when auto-focusing on open (#3077).
useLayoutEffect(() => {
  if (!isHydrated || !focusable) return;
  onFocusableItemAdd();
  return () => onFocusableItemRemove();
}, [isHydrated, focusable, ...]);
// Pre-hydration: passive effect — layout effects mid-hydration force a
// synchronous re-render during hydration.
React.useEffect(() => { /* same body, gated !isHydrated */ });

function getDirectionAwareKey(key: string, dir?: Direction) {
  if (dir !== Direction.RTL) return key;
  return key === 'ArrowLeft' ? 'ArrowRight' : key === 'ArrowRight' ? 'ArrowLeft' : key;
}
```

**Flow:** group focus (keyboard-only — mousedown sets isClickFocusRef so Safari's click-focus quirk doesn't hijack) dispatches cancelable ENTRY_FOCUS → candidate ladder `[activeItem, currentItem, ...items]` deduped via filter(Boolean) → focusFirst walks candidates stopping when activeElement actually changed → arrows map through orientation filters + RTL mirroring to first/last/prev/next intents → loop mode wraps via `wrapArray(candidates, currentIndex+1)` else slices forward → all imperative focus deferred inside setTimeout (React#20332 batching hazard) → Shift+Tab on any item sets isTabbingBackOut, dropping GROUP tabIndex to -1 so Tab exits the whole widget.
**Invariant:** the group's own tabIndex is COUNT-DRIVEN, not static — zero focusable items must yield tabIndex=-1 or keyboard users land on a dead container; hydration split is load-bearing both directions (layout-effect pre-paint vs passive-during-hydration); positive-tabIndex DOM-order override applies here too.
**Probe:** direct test `packages/react/roving-focus/src/roving-focus-group.test.tsx`. Byte-exact anchors: `bash -c "cd /mnt/hdd/utopia/inspo/external/ui-radix-ui && grep -nF \"key === 'ArrowLeft' ? 'ArrowRight' : key === 'ArrowRight' ? 'ArrowLeft' : key\" packages/react/roving-focus/src/roving-focus-group.tsx"` (:361) and `grep -cF 'onFocusableItemAdd();' packages/react/roving-focus/src/roving-focus-group.tsx"` (=2, both effects present).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-radix-ui", query: "getFocusIntent wrapArray roving tab stop", limit: 10 });
```

## Verdict
Adopt the broker protocol (count-driven group tabIndex + hydration-split registration + intent ladder); adapt the key map if your widget uses different axes; omit the Safari mousedown workaround only for hosts where click-focus works (record browser support). Direct roving-focus-group.test.tsx coverage at this pin.
