<!-- capsule-v2 -->
# Boost & security gates — how does hx-boost hijack anchors/forms, and which ladders keep requests same-origin and eval/script-optional?

**Source:** htmx MIT `master@ad56dff71e55d9c717447437b4c942a64575d4b2` (v2.0.10); Codebase Memory `ext-htmx`. **Question:** What are the exact conditions for boosting an element, and how must a porter reproduce the CSP/safety ladder (selfRequestsOnly, allowEval, allowScriptTags, hx-disable)?

## boostElement + verifyPath + maybeEval: opt-in interception, deny-by-default egress
**Path/Symbol:** `src/htmx.js:boostElement` (:2397-2428); path verification `verifyPath` (:4114-4125) firing `htmx:validateUrl`; eval gate `maybeEval` (:3970-3977); disable selector `eltIsDisabled` (:2388-2390) against `config.disableSelector = '[hx-disable], [data-hx-disable]'`; local-link test `isLocalLink` (:2379-2383).
**Signature:** `function boostElement(elt, nodeData, triggerSpecs)` — eligible: `HTMLAnchorElement && isLocalLink && target ''|'_self'`, OR `FORM` with `method !== 'dialog'` (string-lowercased compare). Verb from form method (default get), path from href/action; missing action ⇒ `location.href`; GET actions drop their query string before parameter re-append (`path.replace(/\?[^#]+/, '')`).
**Data Shape:** Boosted flag lives in nodeData; it flips default swapStyle to innerHTML regardless of hx-swap ("overriding default swap style does not effect boosting"), adds `HX-Boosted: true` header, forces history push of the response path, and scrollIntoViewOnBoost shows top unless anchor link.

### Decisive source
```js
function verifyPath(elt, path, requestConfig) {
  const url = new URL(path, location.protocol !== 'about:' ? location.href : window.origin)
  const origin = location.protocol !== 'about:' ? location.origin : window.origin
  const sameHost = origin === url.origin
  if (htmx.config.selfRequestsOnly) { if (!sameHost) { return false } }
  return triggerEvent(elt, 'htmx:validateUrl', mergeObjects({ url, sameHost }, requestConfig))
}
function maybeEval(elt, toEval, defaultVal) {
  if (htmx.config.allowEval) { return toEval() }
  triggerErrorEvent(elt, 'htmx:evalDisallowedError'); return defaultVal
}
```

**Flow (boost click):** listener fires → disabled check → shouldCancel prevents default for submit-button/link clicks → ctrl/meta-click on boosted anchors passes THROUGH to the browser (`ignoreBoostedAnchorCtrlClick`) so users can open in new tabs → issueAjaxRequest(get|method, path).
**Invariant:** Egress control is TWO-layered: config gate (`selfRequestsOnly`, default TRUE since it protects naive embedders) plus a vetoable event (`htmx:validateUrl` can cancel cross-origin even when config allows, and its detail carries `sameHost`). The about: protocol guard handles sandboxed docs where location.origin is opaque. Script policy is structural: makeFragment either duplicates scripts (nonce applied) or strips them — there is no third state. Eval gating wraps EVERY compiled surface: trigger conditionals, hx-on handlers, js:/javascript: prefixed headers/vals/vars.
**Flow:** `[hx-disable]` freezing works at THREE depths — processNode skips+cleans the subtree, per-click handler checks eltIsDisabled (cleaning on demand), and hx-on listeners self-check.

**Probe:** Boost table `test/attributes/hx-boost.js`: basic anchor :11 / data-prefix :82, dialog-method exclusion :74, explicit-target anchors not boosted :104, HX-Boosted header :110, GET action query-strip :122 vs POST keeps query :135, empty/no-action parameter clearing :147/:159/:184, ctrlKey pass-through :210. Security ladder `test/core/security.js`: selfRequestsOnly off/on egress tests :140/:215, validateUrl cancel trio :228/:247/:268, script-strip via allowScriptTags :292, hx-disable family :11-139. Executed headless: n/a beyond shared batteries.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-htmx", query: "boostElement boost anchor form verify path", limit: 5 });
```
(companion rank-1 hits: `getTriggerSpecs` family resolves boost-adjacent queries; verifyPath reachable via "selfRequestsOnly validateUrl")

## Verdict
Adopt deny-by-default egress with an escape-hatch EVENT (not just a flag), and the three-surface eval gate. Adapt the disable selector constant to your attribute namespace. Omit the about:-protocol branch only for non-browser hosts.
