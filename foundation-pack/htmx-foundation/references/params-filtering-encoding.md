<!-- capsule-v2 -->
# hx-params filtering & encoding negotiation — how do param allowlists and multipart/urlencoded/json bodies interact?

**Source:** htmx MIT `master@ad56dff71e55d9c717447437b4c942a64575d4b2` (v2.0.10); Codebase Memory `ext-htmx`. **Question:** How does hx-params filter collected values, when does a request become multipart, and how can an extension take over encoding entirely?

## filterValues + usesFormData + encodeParamsForBody
**Path/Symbol:** `src/htmx.js:filterValues` (:3723-3749); encoding decision `usesFormData` (:3821-3824: closest `hx-encoding === 'multipart/form-data'` OR matching `<form enctype>`), encoder `encodeParamsForBody` (:3832-3850) + urlEncode/appendParam (:3661-3684) + formDataFromObject (:4131-4146).
**Signature:** `function filterValues(inputValues, elt)` — paramsValue from getClosestAttributeValue (INHERITED): `'none'` ⇒ empty FormData; `'*'` ⇒ pass-through; leading `'not '` ⇒ delete listed names; otherwise allowlist rebuild preserving multi-values via getAll/append.
**Data Shape:** Encoding ladder in encodeParamsForBody: (1) any extension's `encodeParameters(xhr, parameters, elt)` returning non-null WINS; (2) else multipart if negotiated (real FormData, force-materialized through overrideFormData(new FormData(), formDataFromObject(...)) to unwrap the proxy — issue #2317); (3) else urlencoded string.
**Data Shape:** appendParam JSON-stringifies `[object Object]` values before encodeURIComponent; arrays expand to repeated keys.

### Decisive source
```js
function encodeParamsForBody(xhr, elt, filteredParameters) {
  let encodedParameters = null
  withExtensions(elt, function(extension) {
    if (encodedParameters == null) { encodedParameters = extension.encodeParameters(xhr, filteredParameters, elt) }
  })
  if (encodedParameters != null) { return encodedParameters }
  if (usesFormData(elt)) {
    // Force conversion to an actual FormData object ... filteredParameters is a formDataProxy
    return overrideFormData(new FormData(), formDataFromObject(filteredParameters))
  }
  return urlEncode(filteredParameters)
}
```

**Flow:** collect → filter (hx-params) → cache-buster maybe → configRequest mutation → GET/delete-style verbs serialize into URL instead (`useUrlParams`) unless the verb was removed from methodsThatUseUrlParams.
**Invariant:** The proxy-to-real-FormData materialization is NOT cosmetic: XHR send() rejects a Proxy whose target is FormData in some engines (#2317). Extension-first encoding is how JSON-body support exists without core knowing JSON. Filtering runs on the MERGED set (form+includes+submitter+expressionVars) so hx-params governs the final wire shape, not intermediate lanes. Content-Type header is only set for urlencoded non-GET — multipart must keep the browser-generated boundary header.

**Probe:** Filter grammar `test/attributes/hx-params.js`: "none excludes all params" :11, '"*" includes all params' :29, "named includes works" :47, "named exclude works" :65 (+data-prefix :83). Multipart: `test/core/ajax.js` "multipart/form-data encoding works" :816. JSON-via-extension: `test/core/extensions.js` "encodeParameters works as expected" :58; Content-Type override test :383 ("ajax api Content-Type header override to application/json"). Executed headless: filterValues battery (none/*, allowlist p1,p2 dropping secret, not-secret) + urlEncode array expansion.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-htmx", query: "filterValues hx-params encodeParamsForBody multipart urlencoded", limit: 5 });
```
(companion rank-1: overrideFormData resolves value-merge queries)

## Verdict
Adopt the three-stage encoder ladder and inherited-filter semantics. Adapt multipart negotiation to fetch's body typing (FormData vs URLSearchParams). Omit extension encoding hooks only with a documented break for JSON-API integrations that rely on them.
