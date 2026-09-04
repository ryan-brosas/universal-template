<!-- capsule-v2 -->
# Form-field hoisting — how do hidden inputs land inside a real <form> when the component renders in a Portal?

**Source:** Headless UI MIT `main@eea57cf46fd6767ed1059012f7073b88eb159fba`; Codebase Memory `ext-ui-headlessui`. **Question:** What are the objectToFormEntries encoding rules and the FormFieldsProvider/HoistFormFields portal mechanism?

## objectToFormEntries / attemptSubmit / FormFields / HoistFormFields
**Path/Symbol:** `packages/@headlessui-react/src/utils/form.ts:5-75`; `packages/@headlessui-react/src/internal/form-fields.tsx:10-108`.
**Signature:** `objectToFormEntries(source?, parentKey? = null, entries? = []): [string, string][]`; `attemptSubmit(elementInForm: HTMLElement): void`; `FormFields({ data, form?: string, disabled?, onReset?, overrides? })`.
**Data Shape:** flat `[name, value]` pairs; bracket key paths (`parent[child]`, `arr[0]`); booleans→'1'/'0', Date→ISO, null/undefined→'', plain objects recurse (React elements EXCLUDED via isValidElement).

### Decisive source
```ts
function composeKey(parent: string | null, key: string): string {
  return parent ? parent + '[' + key + ']' : key
}
// attemptSubmit prefers CLICKING a real submit button over requestSubmit:
for (let element of form.elements) {
  if ((element.tagName === 'INPUT' || element.tagName === 'BUTTON') && element.type === 'submit' ||
      (element.nodeName === 'INPUT' && element.type === 'image')) { element.click(); return }
}
form.requestSubmit?.()   // never form.submit() — that skips submit events/listeners

// HoistFormFields portals children into the marker rendered inside the REAL <form>:
export function HoistFormFields({ children }) {
  let { target } = useContext(FormFieldsContext)
  return target ? createPortal(<>{children}</>, target) : null   // null until marker mounted
}
```

**Flow:** FormFieldsProvider renders children PLUS a Hidden ref-marker → wherever the Switch/Listbox actually renders (possibly portalled), HoistFormFields portals one `input[type=hidden][readonly][form=id]` per entry into that marker → browser submits them with the real form even though React tree says otherwise. FormResolver finds the form by id or by closest('form') from a probe input.
**Invariant:** entries must be STRINGS (HTML form values); the submit-button click path exists because requestSubmit ignores preventDefault listeners on the button's click handler; hidden inputs render NOTHING until the target marker exists (no hydration mismatch).
**Probe:** direct test `packages/@headlessui-react/src/utils/form.test.ts` pins nested/array/boolean/date/null encodings end-to-end. Deterministic check executed: composeKey nesting and value coercion ladder match source. Graph probe resolves attemptSubmit line-exact.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-headlessui", query: "attemptSubmit requestSubmit", name_pattern: "^attemptSubmit$", limit: 5 });
```

## Verdict
Adopt the encoding table and portal-to-marker pattern verbatim for any headless form control; adapt marker placement to your form context; omit overrides/onReset if unused. The click-submit-over-requestSubmit rationale is a browser-behavior invariant — don't "simplify" it away.
