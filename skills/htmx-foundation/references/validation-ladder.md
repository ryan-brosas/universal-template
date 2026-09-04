<!-- capsule-v2 -->
# Validation ladder — when do HTML5 constraint checks run, and how do they halt a request?

**Source:** htmx MIT `master@ad56dff71e55d9c717447437b4c942a64575d4b2` (v2.0.10); Codebase Memory `ext-htmx`. **Question:** Which inputs get validated during value collection, which events surround a failure, and what suppresses validation entirely?

## validateElement + getInputValues gating: validate only on direct form submission
**Path/Symbol:** `src/htmx.js:validateElement` (:3561-3579); gate computed in `getInputValues` (:3614-3619); halt point in `issueAjaxRequest` (:4505-4510).
**Signature:** gate: `(elt instanceof HTMLFormElement && elt.noValidate !== true) || getAttributeValue(elt,'hx-validate')==='true'`, further ANDed with `!(lastButtonClicked.formNoValidate === true)`; errors accumulate as `{elt, message, validity}`.
**Data Shape:** Per element: only if `willValidate`: fire `htmx:validation:validate`, then `checkValidity()`; on failure fire vetoable `htmx:validation:failed` (detail message+validity), optionally `reportValidity()` (first error only, and only when `config.reportValidityOfForms`), push into errors.

### Decisive source
```js
let validate = (elt instanceof HTMLFormElement && elt.noValidate !== true) || getAttributeValue(elt, 'hx-validate') === 'true'
if (internalData.lastButtonClicked) { validate = validate && internalData.lastButtonClicked.formNoValidate !== true }
...
if (!element.checkValidity()) {
  if (triggerEvent(element, 'htmx:validation:failed', {...}) && !errors.length && htmx.config.reportValidityOfForms) {
    element.reportValidity()
  }
  errors.push({ elt: element, message: element.validationMessage, validity: element.validity })
}
```

**Flow:** values collection validates while scanning → requestConfig carries errors → after configRequest copy-back, non-empty errors ⇒ `htmx:validation:halted` event and the request NEVER OPENS (`endRequestLock()` still runs so queues drain).
**Invariant:** Validation is tied to the SEMANTICS of form submission, not to htmx requests: an input triggering its own hx-get validates NOTHING (its verb path skips the form lane), matching browser behavior where programmatic submissions skip constraint validation. `novalidate`/`formnovalidate` mirror their native attributes including the clicked-submitter case. reportValidity focuses the FIRST invalid input only (errors.length===0 guard) — later failures are silent. The failed-event veto lets frameworks substitute custom UI per field.
**Flow:** because validation runs inside processInputValue, it covers the related form, includes descendants, and submitter buttons uniformly.

**Probe:** `test/core/validation.js`: "HTML5 required validation error prevents request" :11, "Novalidate skips form validation" :28, "Validation skipped for indirect form submission" :41, "Formnovalidate skips form validation" :55, pattern :69, custom :87/:105/:123/:141, "calls htmx:validation:failed on failure" :161, focus/report pairing :179 vs :201 vs preventDefault :222.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-htmx", query: "validateElement checkValidity validation halted errors", limit: 5 });
```
(companion: getInputValues resolves rank-1 for query "getInputValues form data button submitter priority override")

## Verdict
Adopt the direct-submission-only gate and the halted-before-open ordering (a validation failure must never leave a half-sent request). Adapt reportValidity to your UI framework's error surface. Omit nothing else — every suppression flag maps to a native attribute users already know.
