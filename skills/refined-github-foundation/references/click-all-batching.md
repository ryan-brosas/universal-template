<!-- capsule-v2 -->
# Batch Click & Scroll Preservation — how do you alt-click one toggle and flip all siblings while keeping the viewport stable?

**Source:** refined-github MIT `main@3bbe6088fe301d0d5cf1ae751a49307005762a68`; Codebase Memory `refined-github`. **Question:** What is the click-all contract (gates, scroll anchor, selector-vs-function) and the shift-click range algorithm?

## Connected graph-selected seam
**Path/Symbol:** `source/helpers/click-all.ts` (:1–28); `source/helpers/get-items-between.ts` (:1–8, direct test); consumer exemplar `source/features/batch-mark-files-as-viewed.tsx:batchToggle` (:72–91).
**Signature:** `clickAll = mem((selector: string | ((clicked: HTMLElement) => string)): EventHandler => …)`; `getItemsBetween<T>(items: T[], previous: T | undefined, current: T): T[]`.
**Data Shape:** memoized factory — one handler per selector string; handler gates on `event.altKey && event.isTrusted`.

### Decisive source
```ts
// parentElement is the anchor because clickedItem might be hidden/replaced after the click
const resetScroll = preserveScroll(clickedItem.parentElement!);
clickAllExcept(typeof selector === 'string' ? selector : selector(clickedItem), clickedItem);
resetScroll();
```
```ts
// preserve-scroll: remember an anchor element's viewport offset, restore after mutation
const originalPosition = anchor.getBoundingClientRect().top;
return () => requestAnimationFrame(() => {
	window.scrollBy(0, anchor.getBoundingClientRect().top - originalPosition);
});
```
```ts
// Range select: both ends INCLUDED; missing previous starts at index 0
const start = previous ? items.indexOf(previous) : 0;
return items.slice(Math.min(start, end), Math.max(start, end) + 1);
```

**Flow:** alt+trusted click → save scroll anchor (the PARENT of the clicked item, not the item — it may be hidden by the toggle) → click every matching sibling except the origin (the origin's own native handler already fired) → rAF-deferred scroll restoration. Shift-click variant: module-level `previousFile` remembered per delegation scope, cleared via `onAbort(signal, () => {previousFile = undefined})`; range computed over CURRENT file list; each candidate must pass `checkVisibility()` (filters hidden/filtered-out rows) and only toggles files whose checked state differs from the target's ORIGINAL state.
**Invariant:** the scroll anchor must outlive potential replacement of the clicked node. The batch-toggle compares each file against the ORIGIN'S PRE-CLICK state, not against the running result — comparing live state would produce alternating on/off instead of uniformity. Synthetic `.click()` events carry `isTrusted: false`, which is exactly what prevents recursion through the same gated handler.
**Probe:** `source/helpers/get-items-between.test.ts` pins range math directly (both-ends-inclusive, missing-previous); batch behavior pinned by recorded Test URLs in the feature file; scroll preservation source-cited. Partial coverage caveat.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "refined-github", query: "clickAllExcept preserveScroll getItemsBetween batchToggle", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt for any bulk-toggle UI over generated lists. Adapt gating keys and selector derivation. Omit the memoized-factory wrapper if handlers are static. Direct test covers range math; DOM behavior caveat-recorded.
