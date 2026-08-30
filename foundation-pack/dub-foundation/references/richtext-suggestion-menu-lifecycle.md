<!-- capsule-v2 -->
# Suggestion menu lifecycle via ReactRenderer — how do I drive an imperative floating menu for "/" or "@" style completion without leaking DOM or losing keyboard control?

**Source:** dub (AGPL-3.0; EE portions under apps/web/app/(ee)/LICENSE.md) `main@29df217a`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-dub`. **Question:** What is the render/update/keydown/destroy contract between TipTap's suggestion plugin and a React menu component?

## variables.tsx suggestions()
**Path/Symbol:** `packages/ui/src/rich-text-area/variables.tsx:suggestions` (42–111) + `updatePosition` (20–40) + `Menu` (118–322).
**Signature:** `suggestions(variables: string[], variableInfo?): {items({query}), render(): {onStart, onUpdate, onKeyDown, onExit}}`.
**Data Shape:** items = filtered/ranked/paged variable names (max 10); menu element appended to `document.body`, positioned absolutely against a virtual rect from `posToDOMRect(editor.view, from, to)`.

### Decisive source
```tsx
render: () => {
  let component: any;                        // one per suggestion session
  return {
    onStart(props) {
      component = new ReactRenderer(Menu, { props, editor: props.editor });
      document.body.appendChild(component.element);
      updatePosition(props.editor, component.element);   // floating-ui computePosition
    },
    onUpdate(props) { component.updateProps({...props, variableInfo}); updatePosition(…); },
    onKeyDown(props) {
      const handled = component.ref?.onKeyDown(props);    // imperative handle bridge
      if (handled) return true;
      if (props.event.key === "Escape") { component.destroy(); return true; }
      return false;
    },
    onExit() { component.element.remove(); component.destroy(); },
  };
},
```

**Flow:** `@` triggers → onStart mounts Menu off-DOM-tree → onUpdate re-renders + repositions as query changes → keydown flows THROUGH the React component first (via useImperativeHandle ref) so ArrowUp/Down/Enter/Escape work while the editor keeps focus → Escape inside the menu destroys directly; session exit removes the element THEN destroys the renderer.
**Invariant:** `element.remove()` before `component.destroy()` on exit — destroy alone leaks the mounted div in body; the keydown bridge must return true only when consumed, else typing continues to insert text; selection-rect positioning (not mouse position) keeps the menu anchored during scroll.
**Probe:** `grep -c 'component.destroy()' packages/ui/src/rich-text-area/variables.tsx` → **2**; `grep -n 'onExit' packages/ui/src/rich-text-area/variables.tsx` → line 105; `grep -c 'slice(0, 10)' packages/ui/src/rich-text-area/variables.tsx` → **2**.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-dub", query: "suggestions updatePosition ReactRenderer", limit: 5 });
```

## Verdict
Adopt the ReactRenderer lifecycle verbatim for any suggestion UI (slash commands, emoji pickers); adapt ranking (`startsWith > includes`, then alphabetical) and page size to your data; omit floating-ui in favor of your popover lib but keep posToDOMRect anchoring.
