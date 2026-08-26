<!-- capsule-v2 -->
# Header construction & trigger-header protocol — what does htmx send, and how are HX-Trigger response headers turned back into events?

**Source:** htmx MIT `master@ad56dff71e55d9c717447437b4c942a64575d4b2` (v2.0.10); Codebase Memory `ext-htmx`. **Question:** Which request headers are mandatory, how are non-ASCII values protected, and what grammar do HX-Trigger* RESPONSE headers use?

## getHeaders + safelySetHeaderValue + handleTriggerHeader
**Path/Symbol:** `src/htmx.js:getHeaders` (:3696-3713); safe set (:4013-4023); response-trigger parsing `handleTriggerHeader` (:2066-2088) dispatched from handleAjaxResponse for HX-Trigger (pre-load), HX-Trigger-After-Swap, HX-Trigger-After-Settle; header sniffing helper `hasHeader(xhr, regexp)` over getAllResponseHeaders.
**Signature:** base headers: `{'HX-Request':'true', 'HX-Trigger': elt id (raw), 'HX-Trigger-Name': elt name (raw), 'HX-Target': target id, 'HX-Current-URL': location.href}` then hx-headers merged via getValuesForElement walk (`js:`/`javascript:` prefixes force evaluation; `'unset'` value ABORTS the whole chain returning null), plus `HX-Prompt`, plus `HX-Boosted:'true'` when boosted; Content-Type appended in issueAjaxRequest only for non-GET/non-multipart.
**Data Shape:** Response side accepts TWO shapes per header: JSON object body (`{eventName: detailValue|{...detail}}`) or comma-separated event-name list with empty-detail events. Detail objects may carry their own `target` (element override).

### Decisive source
```js
function safelySetHeaderValue(xhr, header, headerValue) {
  if (headerValue !== null) {
    try { xhr.setRequestHeader(header, headerValue) }
    catch (e) { // On an exception, try to set the header URI encoded instead
      xhr.setRequestHeader(header, encodeURIComponent(headerValue))
      xhr.setRequestHeader(header + '-URI-AutoEncoded', 'true')
    }
  }
}
function handleTriggerHeader(xhr, header, elt) {
  const triggerBody = xhr.getResponseHeader(header)
  if (triggerBody.indexOf('{') === 0) {
    const triggers = parseJSON(triggerBody)
    for (const eventName in triggers) {
      let detail = triggers[eventName]
      if (isRawObject(detail)) { elt = detail.target !== undefined ? detail.target : elt }
      else { detail = { value: detail } }
      triggerEvent(elt, eventName, detail)
    }
  } else {
    const eventNames = triggerBody.split(',')
    for (...) { triggerEvent(elt, eventNames[i].trim(), []) }
  }
}
```

**Flow:** request headers built BEFORE configRequest (so handlers can mutate them); values may be static JSON OR evaluated code; the ancestor walk lets a top-level element declare headers for all descendants. On the wire, illegal header characters throw synchronously inside setRequestHeader — hence the encode-and-tag fallback which SERVERS must recognize (`<name>-URI-AutoEncoded: true`).
**Invariant:** Timing is three-phase: HX-Trigger fires before htmx:beforeOnLoad (events land while the old DOM still stands), -After-Swap after swap but before settle completes, -After-Settle last; each phase re-targets to document.body when the requesting element was removed by its own swap ("should handle simple string HX-Trigger-After-Swap ... w/ outerHTML swap"). Raw attribute reads (not closest-inherited) feed HX-Trigger/HX-Target ids — inheritance would misattribute events.

**Probe:** Request-side: `test/core/headers.js` "should include the HX-Request header" :14 through HX-Target :44; non-ASCII safety "set header works with non-ASCII values" internals-adjacent at headers.js:52. Response-side: simple string :54, dot-path :67, case-insensitive name :80, namespaced :93, JSON :106, array-arg JSON :121; phase timing trio :332/:366 with outerHTML swaps; comma lists :346/:380.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-htmx", query: "getHeaders HX-Trigger handleTriggerHeader safelySetHeaderValue", limit: 5 });
```
(companion rank-1: getValuesForElement family)

## Verdict
Adopt the five mandatory headers verbatim — they are the wire contract every server library encodes against. Adapt the URI-encoded fallback to fetch (which throws on invalid header values differently). Omit js:-evaluation of headers under strict CSP (allowEval=false degrades to parseJSON path automatically).
