<!-- capsule-v2 -->
# Value collection & priority FormData — how are inputs, forms, includes, and the clicked button merged without duplicates?

**Source:** htmx MIT `master@ad56dff71e55d9c717447437b4c942a64575d4b2` (v2.0.10); Codebase Memory `ext-htmx`. **Question:** When a request fires, which values are collected in what order, and how do form values override element values without double-submitting the same input?

## getInputValues: two FormData lanes merged by overrideFormData
**Path/Symbol:** `src/htmx.js:getInputValues` (:3602-3653) with `processInputValue` (:3521-3555), `shouldInclude` (:3451-3465), `overrideFormData` (:3587-3595), `getRelatedForm` (:2853-2856), submitter tracking `initButtonTracking`/`maybeSetLastButtonClicked` (:2877-2884, :2823-2829).
**Signature:** `function getInputValues(elt, verb)` → `{errors, formData, values}` where `values = formDataProxy(formData)`; `function overrideFormData(receiver, donor)` deletes every donor key from receiver then appends donor entries.
**Data Shape:** Two lanes: `formData` (element + hx-includes) and `priorityFormData` (related FORM on non-GET verbs + clicked submitter's name/value). Validation runs per input only when `(form direct-submitted && !noValidate) || hx-validate="true"`, further suppressed by `lastButtonClicked.formNoValidate`.

### Decisive source
```js
if (verb !== 'get') { processInputValue(processed, priorityFormData, errors, getRelatedForm(elt), validate) }
processInputValue(processed, formData, errors, elt, validate)
if (internalData.lastButtonClicked || elt.tagName === 'BUTTON' ||
   (elt.tagName === 'INPUT' && getRawAttribute(elt, 'type') === 'submit')) {
  const button = internalData.lastButtonClicked || (elt)
  addValueToFormData(getRawAttribute(button, 'name'), button.value, priorityFormData)
}
const includes = findAttributeTargets(elt, 'hx-include')
forEach(includes, function(node) {
  processInputValue(processed, formData, errors, asElement(node), validate)
  if (!matches(node, 'form')) { forEach(asParentNode(node).querySelectorAll(INPUT_SELECTOR), ...) }
})
// values from a <form> take precedence, overriding the regular values
overrideFormData(formData, priorityFormData)
```

**Flow:** stale `lastButtonClicked` is cleared if it left the DOM → non-GET pulls the related form into the PRIORITY lane (GET deliberately excludes it — "Input doesnt include form on get") → element itself → submitter value → explicit includes (+ their INPUT_SELECTOR descendants when not a form) → priority lane overrides.
**Invariant:** Dedup is positional, not by name: `processed[]` marks seen nodes; when the form itself is processed AFTER an input already added, `removeValueFromFormData(input.name, ...)` surgically removes that one value so `new FormData(form)` won't duplicate it. `shouldInclude` skips empty names, disabled elements (incl. inside `fieldset[disabled]`), button/submit/reset types, unchecked checkbox/radio; file inputs contribute their FileList; multi-select contributes all checked options. SHARP EDGE for porters: `shouldInclude` line `elt.tagName === 'image' || elt.tagName === 'file'` compares against LOWERCASE tagName values that can never occur (HTMLImageElement's tag is `img`) — a case-mismatch inherited from jQuery serialize; harmless but must not be "fixed" into excluding `<img>` unintentionally. Button tracking listens to click AND focusin/focusout (OSX buttons don't focus on click), storing `lastButtonClicked` on the FORM's internal data.

**Probe:** `test/core/parameters.js`: "Input doesnt include form on get" :32, "Double values are included as array" :68, "form does not include button when focus is lost" :161, "it puts GET params in the URL by default" :193 vs DELETE-in-body default :220. Submitter removal pinned at `test/core/api.js:567` "values api returns formDataProxy ... even if clicked button removed". Executed headless: urlEncode of array values (`{a:1,b:['x','y']} → 'a=1&b=x&b=y'` via appendParam object→JSON branch guarded by tests "appendParam can process objects" internals.js:195).

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-htmx", query: "getInputValues form data button submitter priority override", limit: 4 });
```
(rank-1 `src.htmx.overrideFormData src/htmx.js 3587-3595`)

## Verdict
Adopt the dual-lane merge and the positional dedup exactly; both encode subtle browser interop (form.elements iteration vs FormData reconstruction). Adapt validation gating to your framework's validity model. Omit the dead lowercase-tagName comparisons only WITH a comment citing this capsule — they are observable no-ops today.
