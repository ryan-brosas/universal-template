<!-- capsule-v2 -->
# TreeView lazy diff expansion - how does a lazy tree stay consistent when the host both answers expands and prunes children?

**Source:** PhpStorm Light installed build PS-262.9421 (proprietary; cite-only); Codebase Memory `jetbrains-phpstorm-light`. **Question:** What wire contract lets a page-side tree request children lazily while the host can still add/remove nodes out of band?

## webConsole TreeView.Item
**Path/Symbol:** `plugins/javascript-debugger/webConsole/TreeView.js:class Item` (:28-142); `expand` (:83-113), `addChild` (:115-126), `collapse` (:128-140); node type gate `hasChildren()` = `printable.type === PRINTABLE_TYPES.TREE` (:79-81).
**Signature:** `expand()` → `callJVM('expand', [printable.id], callback, true)` (PRESERVED callback — see webconsole-jsbridge-callback-registry); callback receives `[add, children]`; `collapse()` → `callJVM("collapse", [id])`.
**Data Shape:** two callback payloads: `add=true` ⇒ `children = [{first: childPrintable, second: index}]` INSERT pairs; `add=false` ⇒ `children = [index...]` REMOVE indices into the current child list. `childrenItems: Item[]` mirrors `childContainer.childNodes`.

### Decisive source
```js
let callbackId = callJVM('expand', [this.printable.id], ([add, children]) => {
  if (add) for (let childAndIndex of children) {
    let childItem = new Item(childAndIndex.first);
    if (childPrintable.type === 'MESSAGE_TREE_NODE') { /* dblclick/Enter → callJVM('messageNodeCallback',[id]) */ }
    this.addChild(childAndIndex.second, childItem);       // index-positioned insert
  }
  else for (let index of children) {                       // host-initiated pruning
    this.childrenItems.splice(index, 1);
    this.childContainer.removeChild(this.childContainer.childNodes[index]);
  }
}, true);                                                  // preserveCallback: replayable
this.collapsed = false;                                    // SYNCHRONOUS, before callback arrives
```
```js
collapse() {
  clearContainer(this.childContainer);
  callbackMap.delete(this.callbackId);   // kill a still-pending expand reply: no stale re-entry
  callJVM("collapse", [this.printable.id]);
  this.collapsed = true;
  this.firstNavigatable.nextNavigatable = null;            // navigatable tail resets to just itself
  this.lastNavigatable = this.firstNavigatable;
}
addChild(index, childItem) {
  if (index != null && index < this.childrenItems.length) { // positional: DOM + array + ring in lockstep
    insertBefore(...); childrenItems.splice(index, 0, childItem); addNavigatableBefore(prevChild, childItem);
  } else { appendChild/push/addNavigatable }               // null or overflow index ⇒ append
}
```

**Flow:** A TREE-type item renders only its preview until expanded. Expand asks the JVM and treats the answer as a DIFF: pairs to insert at given indices, or bare indices to remove. Collapse clears the DOM container, deletes the pending callback id from the shared `callbackMap` (so a late JVM reply finds nothing), notifies the host, and truncates the navigatable ring tail so hidden children leave the keyboard order.
**Invariant:** the SAME channel is additive (add=true) and subtractive (add=false) — one verb, discriminated union; collapsed flag flips synchronously so double-click cannot double-request; every mutation keeps THREE structures aligned (DOM childContainer, childrenItems array, navigatable DLL); preserved callbacks mean the host may re-push later diffs through the same id.
**Probe:** DOM-bound → byte-exact content pins executed: `callbackMap.delete(this.callbackId);` → TreeView.js:131; `firstNavigatable.nextNavigatable = null;` → :135; whole-file read confirms `[add, children]` destructure at :85-106.
**Coverage caveat:** coverage no_recorded_issue @ gen 2026-08-24T13:57:05Z.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-phpstorm-light", query: "tree item expand collapse children", file_pattern: "*TreeView*", limit: 5 });
```

## Verdict
Adopt the add/remove-index diff contract for any lazy tree over a stateful backend that mutates concurrently (debugger views, live resource trees). Adapt payload shape but keep the discriminated flag. Always cancel pending lazy loads on collapse by deleting the registered callback, not by ignoring replies.
