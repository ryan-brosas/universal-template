<!-- capsule-v2 -->
# composeEventHandlers prevention gate — what is the one contract that lets consumers override library event behavior with preventDefault?

**Source:** radix-ui/primitives MIT `main@f7ecd5ab16f5e1e820eb5786a1419a98a2d594ae`; Codebase Memory `ext-ui-radix-ui`. **Question:** How are user handlers and internal handlers chained so preventDefault stays meaningful, and how is activeElement resolved inside iframes?

## Connected graph-selected seam
**Path/Symbol:** `packages/core/primitive/src/primitive.tsx:composeEventHandlers` (:11-23), `getActiveElement` (:45-71), `dispatchDiscreteCustomEvent` (imported by dismissable-layer for pointer-down-outside), `Primitive` component family (attribute passthrough + asChild slot rendering).
**Signature:** `composeEventHandlers<E extends {defaultPrevented}>(original?, ours?, {checkForDefaultPrevented = true}?) → (event) => void`; `getActiveElement(node, activeDescendant = false) → HTMLElement | null`.
**Data Shape:** returns a single handler running original FIRST then ours unless gated off or already default-prevented; getActiveElement recurses through iframe contentDocuments.

### Decisive source
```ts
export function composeEventHandlers<E extends { defaultPrevented: boolean }>(
  originalEventHandler?: (event: E) => void,
  ourEventHandler?: (event: E) => void,
  { checkForDefaultPrevented = true } = {},
) {
  return function handleEvent(event: E) {
    originalEventHandler?.(event);
    if (checkForDefaultPrevented === false || !event || !event.defaultPrevented) {
      return ourEventHandler?.(event);
    }
  };
}
```
iframe/aria descent:
```ts
if (isFrame(activeElement) && activeElement.contentDocument) {
  return getActiveElement(activeElement.contentDocument.body, activeDescendant);
}
if (activeDescendant) {
  const id = activeElement.getAttribute('aria-activedescendant');
  ...
}
```

**Flow:** every radix event prop composes consumer-first (`composeEventHandlers(props.onClick, internal)`) — consumer preventDefault suppresses the internal step wherever the gate applies; opt-out via third arg when internal logic must run regardless (e.g. Select trigger focus forcing). The iframe-piercing activeElement resolver backs focus-management checks (`document.activeElement !== PREVIOUSLY_FOCUSED_ELEMENT` loops still work when focus moved into a frame); empty-object activeElement (cross-origin iframe quirk) guarded via nodeName probe; aria-activedescendant mode resolves the real element by id for composite widgets.
**Invariant:** ORDER is original-then-ours — reversing it steals the consumer's ability to cancel; `checkForDefaultPrevented:false` is reserved for handlers whose internal bookkeeping MUST run (pointer-type tracking, focus forcing). Porters who swap the order break every "preventable" documented prop in the library.
**Probe:** byte-exact anchors: `bash -c "cd $REFERENCE_ROOT/external/ui-radix-ui && grep -nF 'checkForDefaultPrevented === false || !event || !event.defaultPrevented' packages/core/primitive/src/primitive.tsx"` (:19) and `grep -nF 'getActiveElement(activeElement.contentDocument.body, activeDescendant)' packages/core/primitive/src/primitive.tsx"` (:57). Behavior exercised transitively by every component test suite (dismissable-layer prevented-dismiss cases :105/:119 are end-to-end pins of the gate).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-radix-ui", query: "composeEventHandlers defaultPrevented Primitive", limit: 10 });
```

## Verdict
Adopt verbatim (7 lines, zero host coupling); adapt only the discrete-event dispatch helper to your scheduler if you mirror DismissableLayer's custom events; omit the iframe branch only for single-document hosts (record it). No dedicated unit spec for this file at pin — covered transitively by downstream suites; verified by whole-file read + probes.
