<!-- capsule-v2 -->
# Style injector — refcounted cross-root CSS with prepend defense and adopted sheets

**Source:** dnd-kit MIT `main@6fb57833026e06bb3925eef78316ba56d59749c8`; Codebase Memory `ext-ui-dnd-kit`. **Question:** How do plugin styles reach shadow-DOM targets during a drag without leaking after it, and why prepend to `<head>`?

## StyleInjector
**Path/Symbol:** `packages/dom/src/core/plugins/stylesheet/StyleInjector.ts:23-261`.
**Signature:** `register(cssRules): () => void` (plugin-lifetime rules); `addRoot(root): () => void` (extra Document|ShadowRoot); module-global `styleRegistry: Map<Document|ShadowRoot, Map<cssRules, {refCount, cleanup}>>` shared across manager instances.
**Data Shape:** reactive `additionalRoots` Set + derived `roots` = (sourceRoot ∪ targetRoot ∪ additionalRoots) while a drag is initializing/initialized, else EMPTY SET.

### Decisive source
```ts
#inject(root: Document | ShadowRoot, cssRules: string): CleanupFunction {
  let registration = rootStyles.get(cssRules);
  if (!registration) { created = isDocument(root)
      ? this.#injectStyleElement(root, rootStyles, cssRules)     // <style> PREPENDED
      : this.#injectAdoptedSheet(root, rootStyles, cssRules);    // adoptedStyleSheets
    registration.refCount++;
  }
  let disposed = false;
  return () => { if (disposed) return; disposed = true;
    registration.refCount--;
    if (registration.refCount === 0) registration.cleanup(); };
}

// Document path: WHY prepend
// For Document roots, prepend a <style> element to <head> so that any
// @layer declarations appear before layers from regular stylesheets,
// giving them the lowest cascade priority.
style.textContent = cssRules;
root.head.prepend(style);
const observer = new MutationObserver((entries) => {
  for (const entry of entries)
    for (const node of Array.from(entry.removedNodes))
      if (node === style) { root.head.prepend(style); return; }   // self-heal
});
observer.observe(root.head, {childList: true});
```

**Flow:** the effect re-runs whenever roots change → injects every registered rule into every active root → returns a composite cleanup that decrements all refcounts. Refcounting means multiple plugins sharing `Cursor`-style rules (`* { cursor: grabbing !important; }`) or multiple managers targeting one document share ONE DOM node; when the last consumer unregisters, node/sheet removal runs and empty root buckets are deleted from the global map. Shadow roots use `adoptedStyleSheets.push(sheet)` specifically to avoid mutating light DOM children (`:first-child` safety).
**Invariant:** injection happens ONLY while a drag is live (idle ⇒ empty roots ⇒ cleanups run); the MutationObserver must re-prepend rather than re-create (nonce/CSP attributes survive); double-dispose is guarded per cleanup; ShadowRoot cleanup checks `host.isConnected` to avoid touching detached trees.
**Probe:** no dedicated upstream unit file (DOM coverage caveat); consumers pinned by Feedback/Cursor constructor wiring tests in integration stories; port with a jsdom/happy-dom test asserting single-node refcounting.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-dnd-kit", query: "StyleInjector", name_pattern: "^StyleInjector$", limit: 10 });
```

## Verdict
Adopt the global refcount registry + drag-scoped root set + prepend-for-cascade-lowest rule; adapt the nonce option to your CSP story; omit adoptedStyleSheets only if you don't support shadow DOM.
