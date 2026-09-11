<!-- capsule-v2 -->
# Request lifecycle & hx-sync queueing — how does issueAjaxRequest order confirmation, sync strategies, and the request lock?

**Source:** htmx MIT `master@ad56dff71e55d9c717447437b4c942a64575d4b2` (v2.0.10); Codebase Memory `ext-htmx`. **Question:** What is the exact gate order from click to xhr.send, and how do drop/abort/replace/queue first|last|all interleave with the per-element request lock?

## issueAjaxRequest: the full pre-flight ladder
**Path/Symbol:** `src/htmx.js:issueAjaxRequest` (:4269-4650); sync parsing :4330-4361; queue drain `endRequestLock` (:4403-4411); confirm/prompt gates :4317-4430; configRequest copy-back :4491-4503; URL-param verbs :4512-4531; send + progress mirroring :4627-4648.
**Signature:** `function issueAjaxRequest(verb, path, elt, event, etc, confirmed)` → Promise (resolves immediately when gated out; rejects on target/invalid-path/send errors).
**Data Shape:** Lock state lives on the SYNC element's internal data: `{xhr, abortable, queuedRequests[]}`. `etc` carries helper overrides (`targetOverride`, `swapOverride`, `values`, `headers`, `select`, `selectOOB`, `push`, `replace`, `returnPromise`, custom `handler`).

### Decisive source
```js
if (syncStrategy) {
  ...
  // default to the drop strategy
  syncStrategy = (syncStrings[1] || 'drop').trim()
  if (syncStrategy === 'drop' && eltData.xhr && eltData.abortable !== true) { return promise }        // silently drop
  else if (syncStrategy === 'abort') { if (eltData.xhr) { return promise } else { abortable = true } }
  else if (syncStrategy === 'replace') { triggerEvent(syncElt, 'htmx:abort') }                        // kill current, continue
  else if (syncStrategy.indexOf('queue') === 0) { queueStrategy = (queueStrArray[1] || 'last').trim() }
}
if (eltData.xhr) {
  if (eltData.abortable) { triggerEvent(syncElt, 'htmx:abort') }
  else {
    if (queueStrategy == null) { /* fall back to triggerSpec.queue, else 'last' */ }
    if (queueStrategy === 'first' && queued.length === 0) push(reissue)
    else if (queueStrategy === 'all') push(reissue)
    else if (queueStrategy === 'last') { queuedRequests = []; push(reissue) }   // dump existing queue
    return promise                                                              // this call resolves now
  }
}
```

**Flow:** detached-elt early resolve → target resolution (unresolvable ⇒ `htmx:targetError` + reject; DUMMY_ELT `<output>` sentinel for API calls with bad selectors) → submitter formaction/formmethod override (non-verb formmethod resolves WITHOUT issuing) → `htmx:confirm` event (its detail `issueRequest(skipConfirmation)` re-enters with confirmed=true; preventDefault cancels) → hx-sync strategy → prompt → window.confirm → headers (HX-Request/Trigger/Trigger-Name/Target/Current-URL, boosted flag, Content-Type urlencoded unless GET/multipart) → values+expressionVars merge → filterValues → cache-buster → `htmx:configRequest` (mutable; path/verb/headers copied BACK from it) → validation halt → anchor split → URL-params verbs append query string → `verifyPath` same-origin gate (`selfRequestsOnly`) ⇒ `htmx:invalidPath` → open → header set loop (`safelySetHeaderValue` falls back to URI-encoded value + `<name>-URI-AutoEncoded: true`) → beforeRequest veto → indicators/disabled-elts attach AFTER the veto point → xhr.loadend family mirrored as `htmx:xhr:*` events → send.
**Invariant:** The lock is on the sync element but INDICATOR bookkeeping is on the triggering element — they are different elements under `hx-sync`. Every exit path MUST run `maybeCall(resolve/reject)` + `endRequestLock()` or the queue deadlocks. `queue:last` (the default everywhere) DUMPS pending requests rather than appending. Response handling is pluggable via `etc.handler` (default handleAjaxResponse); onload re-fires afterRequest/afterOnLoad on the nearest surviving ancestor when the trigger element was swapped away mid-flight.

**Probe:** Strategy matrix pinned by `test/attributes/hx-sync.js`: "can use drop strategy" :11, "defaults to the drop strategy" :28, replace :45, "queue all" :62, "queue last" :95, "queue first" :128, "abort strategy to end existing abortable request" :161, "drop abortable request when one is in flight" :178, programmatic abort via htmx:abort :195. Target-error funnel at `test/core/api.js:231-270` ("ajax api does not fall back to body when target invalid", "...even if source set").

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-htmx", query: "issueAjaxRequest sync queue abort strategy", limit: 4 });
```
(rank-1 `src.htmx.issueAjaxRequest src/htmx.js 4269-4650`)

## Verdict
Adopt the gate ORDER and the lock/queue mechanics; both are load-bearing for real apps (double-submit protection lives here). Adapt XHR to fetch by mapping each xhr.onload/onerror/onabort/ontimeout arm to its promise resolution point. Omit formmethod/formaction submitter overrides only for non-form hosts. Coverage caveat: runner blocked; behavior verified against the named test blocks at pin.
