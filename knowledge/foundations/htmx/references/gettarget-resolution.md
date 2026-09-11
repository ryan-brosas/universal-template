<!-- capsule-v2 -->
# getTarget resolution — how does the swap target default, and how do hx-target keywords and boost override it?

**Source:** htmx MIT `master@ad56dff71e55d9c717447437b4c942a64575d4b2` (v2.0.10); Codebase Memory `ext-htmx`. **Question:** Given an element firing a request, which node receives the swap when hx-target is absent, `'this'`, an extended selector, or when the element is boosted?

## getTarget: closest-inherited value → this/selector → boosted-body → self
**Path/Symbol:** `src/htmx.js:getTarget` (:1396-1412); `'this'` resolution `findThisElement` (:1386-1390); selector path via querySelectorExt (single result); DUMMY_ELT interplay in issueAjaxRequest (:4290-4295).
**Signature:** `function getTarget(elt)` → Node|Window|null. Precedence: (1) `getClosestAttributeValue(elt,'hx-target')` truthy ⇒ `'this'` resolves to the nearest element actually CARRYING hx-target (`findThisElement` walks up until the attribute exists — so `hx-target="this"` on a PARENT targets that parent, not the trigger), else extended-selector lookup returning FIRST match; (2) no attribute but `nodeData.boosted` ⇒ document.body; (3) else the element itself.
**Data Shape:** Unresolvable selectors return undefined from querySelectorAllExt's first() — issueAjaxRequest converts null/DUMMY_ELT into an `htmx:targetError` event + promise rejection; API-level calls pre-substitute DUMMY_ELT (`<output>`) to avoid ever replacing body by accident.

### Decisive source
```js
function getTarget(elt) {
  const targetStr = getClosestAttributeValue(elt, 'hx-target')
  if (targetStr) {
    if (targetStr === 'this') { return findThisElement(elt, 'hx-target') }
    else { return querySelectorExt(elt, targetStr) }
  } else {
    const data = getInternalData(elt)
    if (data.boosted) { return getDocument().body } else { return elt }
  }
}
```

**Flow:** every request computes target AFTER confirm/sync gates (issueAjaxRequest line ~4290) but response-side HX-Retarget can REPLACE it later (resolveRetarget throws on unresolvable — see response-handling capsule).
**Invariant:** Inheritance is via the disinherit-aware ladder, so `hx-disinherit="hx-target"` on a mid-tree container restores SELF-targeting below it. Boosted anchors without explicit targets swap BODY innerHTML — that is what makes full-page boosting work with partial responses. The `'this'`-on-ancestor semantics surprise porters: the attribute owner is the target, not the clicker.
**Flow:** findAttributeTargets (indicators/disabled/includes) reuses the same `'this'`+selector machinery with MULTI-match and inherit-keyword extensions — one mental model covers all four attributes.

**Probe:** Keyword coverage `test/attributes/hx-target.js`: closest/find/next/previous forms incl. chevron at :155/:174; ajax-api target-error funnel `test/core/api.js` :231/:239/:253/:270 ("does not fall back to body when target invalid" family). Boost-to-body default exercised by hx-boost basic tests :11/:82. Executed headless: n/a beyond shared selector battery.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-htmx", query: "getTarget hx-target this boosted body resolve", limit: 5 });
```
(companion rank-1: querySelectorExt family)

## Verdict
Adopt the three-tier default and the ancestor-owned `'this'` semantics. Adapt the DUMMY_ELT sentinel pattern wherever your host resolves optional targets. Omit nothing else — target mis-resolution is the #1 source of "my whole page got replaced" reports.
