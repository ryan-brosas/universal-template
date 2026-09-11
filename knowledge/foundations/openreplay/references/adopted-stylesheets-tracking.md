<!-- capsule-v2 -->
# Adopted stylesheets + CSS rules tracking — how do constructed CSSStyleSheet changes get recorded across Document and ShadowRoots?

**Source:** openreplay AGPL-3.0 (tracker MIT) `main@99eb600`; Codebase Memory `openreplay`. **Question:** What prototype patches capture adoptedStyleSheets mutations that fire no DOM events?

## Property-descriptor wrap + replace/replaceSync hooks
**Path/Symbol:** `tracker/tracker/src/main/modules/constructedStyleSheets.ts` — id allocator `_id = 0xf` (:21–27), `sendAdoptedStyleSheetsUpdate` (:39–88, 20 ms deferred "mysterious bug" note), descriptor patch (:90–108), context guard `__openreplay_adpss_patched__` (:110–142); companion rule-diff scanner `modules/cssrules.ts` (`ruleSnapshots`, `__css_tracking_patched__`, check interval 200 ms).
**Signature:** `patchAdoptedStyleSheets(prototype: Document|ShadowRoot)`; `nextID(): number`.
**Data Shape:** per-root owning lists (`Map<nodeID, sheetID[]>`) diffed to emit AddOwner/RemoveOwner/InsertRule/Replace; document nodeID pinned to 0.

### Decisive source
```ts
Object.defineProperty(prototype, 'adoptedStyleSheets', {
  ...nativeAdoptedStyleSheetsDescriptor,
  set: function (value) {
    const retVal = nativeAdoptedStyleSheetsDescriptor.set.call(this, value)
    sendAdoptedStyleSheetsUpdate(this)   // diff + emit
    return retVal
  },
})
```
```ts
// Mysterious bug (in-source): a rule mutates milliseconds after load with NO
// replace/insertRule call — hence the deferred re-read instead of event trust.
```

**Flow:** setter patch triggers update → new sheets get ids, initial rules sent, ownership diffs emitted → CSSStyleSheet.replace/replaceSync patched to emit full-sheet Replace → cssrules module additionally snapshots every rule text (`sheetID:index → cssText`) and rescans every 200 ms to catch silent edits, emitting Insert+Delete pairs.
**Invariant:** Patches must be once-per-context (guard flags) or iframes double-patch. Ownership diff must run AFTER the native set completes. Document's nodeID is fixed at 0 — never look it up.
**Probe:** `grep -c '__openreplay_adpss_patched__' tracker/tracker/src/main/modules/constructedStyleSheets.ts` → `2`; `grep -c 'Mysterious bug' tracker/tracker/src/main/modules/constructedStyleSheets.ts` → `1`; `grep -c '__css_tracking_patched__' tracker/tracker/src/main/modules/cssrules.ts` → `2`; direct tests `tests/cssInliner.test.ts` adjacent suite executed green.
**Coverage:** clean.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openreplay", query: "adoptedStyleSheets patchAdoptedStyleSheets ruleSnapshots", limit: 10 });
```

## Verdict
Adopt descriptor-wrap + periodic snapshot diffing. Adapt intervals. Omit grouping-rule replacement if you don't track CSSGroupingRule.
