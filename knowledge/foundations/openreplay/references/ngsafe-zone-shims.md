<!-- capsule-v2 -->
# ngSafe (Angular Zone.js) browser-method shims — why do MutationObserver/addEventListener need Zone-aware wrappers?

**Source:** openreplay AGPL-3.0 (tracker MIT) `main@99eb600`; Codebase Memory `openreplay`. **Question:** How does the tracker avoid Angular's patched globals without breaking non-Angular pages?

## Zone `__symbol__` lookup with opt-out flag
**Path/Symbol:** `tracker/tracker/src/main/utils.ts` — `ngSafeBrowserMethod` (:167–173), `createMutationObserver` (:175–182), `createEventListener/deleteEventListener` (:184+); option plumbing `forceNgOff` (App options :180, Nodes :21).
**Signature:** `ngSafeBrowserMethod(method: string): string`; `createEventListener(target, type, cb, useCapture, forceNgOff)`.
**Data Shape:** When `window.Zone` exists, `Zone.__symbol__('MutationObserver')` returns e.g. `__zone_symbol__MutationObserver` — the UNPATCHED native constructor.

### Decisive source
```ts
export function ngSafeBrowserMethod(method: string): string {
  return window.Zone && '__symbol__' in window.Zone
    ? window['Zone']['__symbol__'](method)
    : method
}
export function createMutationObserver(cb, forceNgOff?) {
  if (!forceNgOff) {
    const mObserver = ngSafeBrowserMethod('MutationObserver')
    return new window[mObserver](cb)
  }
  return new MutationObserver(cb)
}
```

**Flow:** all observers/listeners created through these helpers → on Angular pages the unpatched natives bypass Zone's task tracking (no change-detection storms from capture traffic) → `forceNgOff:true` skips the lookup entirely for hosts that already manage zones.
**Invariant:** The helper returns a NAME looked up on window, not a reference — a porter caching it before Zone loads breaks; resolve lazily at construction. Every listener add/remove pair must go through the same helper or removal misses.
**Probe:** `grep -c "window.Zone && '__symbol__' in window.Zone" tracker/tracker/src/main/utils.ts` → `1`; `grep -c 'forceNgOff' tracker/tracker/src/main/utils.ts` → `6`. Direct tests: none upstream for utils shim (grep-pinned); consumers green via full suite.
**Coverage:** clean.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openreplay", query: "ngSafeBrowserMethod Zone __symbol__ forceNgOff", limit: 10 });
```

## Verdict
Adopt lazy symbol resolution. Adapt for frameworks other than Angular. Omit if no zone-patched host is possible.
