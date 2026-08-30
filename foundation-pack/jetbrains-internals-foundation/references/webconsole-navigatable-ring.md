<!-- capsule-v2 -->
# WebConsole navigatable ring - how does keyboard selection span nested collapsible structures without a global registry?

**Source:** PhpStorm Light installed build PS-262.9421 (proprietary; cite-only); Codebase Memory `jetbrains-phpstorm-light`. **Question:** How do you give arrow-key selection over a DOM tree of nested, collapsible components when each component owns its own children?

## webConsole NavigatablesHost
**Path/Symbol:** `plugins/javascript-debugger/webConsole/WebConsole.js:class NavigatablesHost` (:2-127); consumers: `WebConsole extends NavigatablesHost` (:130), `Message extends NavigatablesHost` (:552), `Item extends NavigatablesHost` (`TreeView.js:28`). Selection drivers `_selectUp/_selectDown` (:507-525); LEFT/RIGHT host-chain walk in `_onKeyEvent` (:158-179).
**Signature:** `addNavigatable(item)`, `addNavigatableBefore(nextItem, newItem)` splice into an intrusive doubly-linked list threaded through the selectable objects themselves (`item.prevNavigatable/.nextNavigatable/.navigatableHost`). Queries: `getPreviousNavigatable(current)` / `getNextNavigatable(current)` / `getFirstNavigatable()` / `getLastNavigatable()`.
**Data Shape:** Every registered item is either a leaf or ANOTHER NavigatablesHost (hosts nest arbitrarily: console → message → tree item). Hosts carry `firstNavigatable`/`lastNavigatable`; items carry back-pointer `navigatableHost`.

### Decisive source
```js
getNextNavigatable(current) {
  let next = current.nextNavigatable;
  while (next) {                       // skip hidden in-loop
    let elem = (next instanceof NavigatablesHost) ? next.getFirstNavigatable() : next;
    if (!isHidden(elem)) break;
    next = next.nextNavigatable;
  }
  if (next instanceof NavigatablesHost) return next.getFirstNavigatable();   // descend
  if (!next && this.navigatableHost)                                         // escape upward
    return this.navigatableHost.getNextNavigatable(this);
  return next;
}
```
(`utils.js:168-170`: `isHidden = !element || element.offsetParent === null` — collapsed subtrees ARE hidden elements.)

**Flow:** Registration happens at construction time (each Message adds its root wrapper; each tree Item adds its `<li>`; link printables register into their message). DOWN walks the flat ring of the current item's host; hitting a host entry descends into its first visible child; falling off the list end escapes recursively to the parent host. LEFT/RIGHT walk UP the `navigatableHost` chain calling `collapseAction()`/`expandAction()` until one returns true — collapse state is exactly what makes items `isHidden`, so the same flag drives both rendering and navigation. Asymmetry note: entering a host always lands on `getFirstNavigatable()`, even in `getLastNavigatable()`'s final branch — correct because you arrive at a host from BELOW only via getPreviousNavigatable, whose walk already positioned you at the host's tail.
**Invariant:** one flat order per host; visibility (offsetParent) is the single source of truth for skippability; no central registry — membership lives on the objects and dies with them.
**Probe:** DOM-bound code cannot execute headless in this lane → byte-exact content pins executed instead: `WebConsole.js:137` gap const, `:248` updateStickToEnd, TreeView.js:135 tail reset, utils.js:169 offsetParent test; plus live graph retrieval below.
**Coverage caveat:** check_index_coverage no_recorded_issue ×4 (WebConsole/TreeView/utils/search.js), freshness metadata_match @ gen 2026-08-24T13:57:05Z.

## Get live surrounding code
```ts
await mcp.codebase_memory.get_code_snippet({ project: "jetbrains-phpstorm-light", qualified_name: "jetbrains-phpstorm-light.plugins.javascript-debugger.webConsole.WebConsole.NavigatablesHost.getNextNavigatable" });
```

## Verdict
Adopt intrusive DLL-per-host with host nesting whenever you need roving-keyboard selection across component-owned regions (log viewers, inspector trees). Adapt the visibility predicate to your renderer's collapse mechanism. Omit the host-escape recursion only if your top-level container owns every region.
