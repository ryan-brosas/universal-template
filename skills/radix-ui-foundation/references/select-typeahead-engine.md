<!-- capsule-v2 -->
# Select typeahead engine — how does typing-ahead move focus/selection without a text input, including repeated-key cycling?

**Source:** radix-ui/primitives MIT `main@f7ecd5ab16f5e1e820eb5786a1419a98a2d594ae`; Codebase Memory `ext-ui-radix-ui`. **Question:** How is typeahead search buffered, decayed, normalized, and matched so single-key cycling and multi-char prefix search both behave like a native select?

## Connected graph-selected seam
**Path/Symbol:** `packages/react/select/src/select.tsx:useTypeaheadSearch` (:1857-1887), `findNextItem` (:1906-1921), `wrapArray` (:1927-1929); consumers: trigger (:322-329 selects the VALUE) and content (:771-782 focuses the ITEM).
**Signature:** `useTypeaheadSearch(onSearchChange) → [searchRef: RefObject<string>, handleTypeaheadSearch(key), resetTypeahead()]`; `findNextItem<T extends {textValue}>(items, search, currentItem?) → T | undefined`.
**Data Shape:** search buffer lives in a ref (no re-render); self-rescheduling timeout resets it to `''` 1000ms after last keystroke; items carry `value/disabled/textValue`.

### Decisive source
```ts
const isRepeated = search.length > 1 && Array.from(search).every((char) => char === search[0]);
const normalizedSearch = isRepeated ? search[0]! : search;
const currentItemIndex = currentItem ? items.indexOf(currentItem) : -1;
let wrappedItems = wrapArray(items, Math.max(currentItemIndex, 0));
const excludeCurrentItem = normalizedSearch.length === 1;
if (excludeCurrentItem) wrappedItems = wrappedItems.filter((v) => v !== currentItem);
const nextItem = wrappedItems.find((item) =>
  item.textValue.toLowerCase().startsWith(normalizedSearch.toLowerCase()),
);
return nextItem !== currentItem ? nextItem : undefined;
```

**Flow:** keydown (length===1, no modifiers — checked at both call sites) appends to buffer → callback receives full buffer → trigger consumer matches against enabled items anchored on `context.value`; content consumer anchors on `document.activeElement` and focuses inside `setTimeout(...)` because imperative focus during keydown races React batching (facebook/react#20332) → match wraps forward from current; buffer decays via nested `updateSearch('')` after 1000ms.
**Invariant:** repeated-character normalization (`'aaa'` ≡ `'a'`) must run BEFORE length checks that treat 1-char searches differently; the exclude-current rule applies only when the NORMALIZED search is one character — otherwise pressing `'ab'` while on item 'Ab' correctly keeps it; matching never moves focus when the current item already matches (multi-char case).
**Probe:** `bash -c "cd /mnt/hdd/utopia/inspo/external/ui-radix-ui && grep -nF \"updateSearch(''), 1000\" packages/react/select/src/select.tsx"` (:1871 decay constant) and `grep -nF 'search.length > 1 && Array.from(search).every((char) => char === search[0])' packages/react/select/src/select.tsx` (:1911 normalization predicate).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-radix-ui", query: "useTypeaheadSearch findNextItem wrapArray", limit: 10 });
```

## Verdict
Adopt the buffer+decay+wrap ladder verbatim (it is host-free); adapt the two consumer wirings (select-value vs focus-item) to your component; omit setTimeout-deferred focus only if your renderer batches differently than React DOM. Direct tests: select.test.tsx exercises keyboard selection paths (`does not select an item from Space/Enter typed into a portaled focusable descendant` :217); the pure matcher itself has no isolated spec — pinned by whole-file read + probe greps at the pin.
