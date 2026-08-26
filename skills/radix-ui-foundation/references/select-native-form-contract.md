<!-- capsule-v2 -->
# Select native form contract — how do you submit a headless widget's value through real form autofill and reset?

**Source:** radix-ui/primitives MIT `main@f7ecd5ab16f5e1e820eb5786a1419a98a2d594ae`; Codebase Memory `ext-ui-radix-ui`. **Question:** How does Select participate in native `<form>` submission/reset/autofill despite rendering no real control until open?

## Connected graph-selected seam
**Path/Symbol:** `packages/react/select/src/select.tsx:SelectBubbleInput` (:1763-1845), form-reset effect in SelectProvider (:198-205), `nativeSelectKey` (:217-219), `SelectItemText` value-node portal (:1526-1534).
**Signature:** `<SelectBubbleInput />` renders `<Primitive.select aria-hidden tabIndex={-1} name autoComplete form disabled required defaultValue={selectValue}>`.
**Data Shape:** `isFormControl = trigger ? !!form || !!trigger.closest('form') : true` (:208 — SSR default TRUE so pre-JS forms still see options); `nativeOptions: Set<ReactElement>` gathered from ItemText layout effects; key = option values joined with `';'`.

### Decisive source
```ts
const setValue = descriptor.set;
if (prevValue !== selectValue && setValue) {
  const event = new Event('change', { bubbles: true });
  setValue.call(select, selectValue);
  select.dispatchEvent(event);
}
```
(no React `value` attribute is ever set — deliberately)

**Flow:** items register synthetic `<option>` elements into provider state → BubbleInput re-mounts WHOLE `<select>` whenever option values change (`key={nativeSelectKey}`) because the browser associates defaultValue only with options rendered simultaneously → value changes are applied via the NATIVE prototype setter then a bubbling `change` Event is dispatched manually so parent form `onChange` handlers fire → form `reset` listener restores `initialValueRef.current`. Selected item's text portals INTO the trigger's value node for display. Visually-hidden styles instead of `display:none` because Safari autofill ignores hidden selects.
**Invariant:** setting the React `value` prop makes React swallow the programmatic change dispatch as a duplicate — the input MUST stay uncontrolled from React's perspective (`defaultValue={selectValue}` only); the empty-value "clear" Item already emits `<option value="">`, so the synthetic placeholder option is suppressed when one exists (`hasEmptyValueOption`) to avoid duplicate empties.
**Probe:** direct tests `packages/react/select/src/select.test.tsx` — form-reset matrix :272-390 (uncontrolled/controlled/external-form), clear-value suite #2706 :77-145 incl. `renders a single empty native option when a clear item is provided` (:124). Byte-exact anchor: `bash -c "cd /mnt/hdd/utopia/inspo/external/ui-radix-ui && grep -nF 'defaultValue={selectValue}' packages/react/select/src/select.tsx"` (:1838).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-radix-ui", query: "SelectBubbleInput nativeOptions form value", limit: 10 });
```

## Verdict
Adopt the whole bridge (prototype-setter dispatch + options-keyed rebuild + reset listener + portal display); adapt the hidden-styling choice if your target browsers differ; omit the external-form lookup (`getElementById(form)` branch) only if your host never uses `form=` attributes. Upstream tests pin behavior directly — this capsule has real coverage.
