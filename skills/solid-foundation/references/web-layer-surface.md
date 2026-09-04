<!-- capsule-v2 -->
# Solid web layer surface — how do Portal/Dynamic sit on the dom-expressions client, and what does solid-js/web actually contain in-repo?

**Source:** SolidJS solid MIT `main@f47845f9cc16ecbb316aa6560c7161f45af9a3d8`; Codebase Memory `solid` (pass-2 refresh: originally authored against the retired `ext-solid` graph at the identical pin; root/HEAD/coverage re-verified 2026-08-25, generation 2026-08-25T20:12:15Z). **Question:** Where is the DOM implementation boundary, and what do Portal and Dynamic add on top?

## packages/solid/web: re-export shim + two components
**Path/Symbol:** `packages/solid/web/src/client.ts` (:1, `export * from "dom-expressions/src/client.js"`), `index.ts` (:1-171): `Portal` (:58-111), `createDynamic` (:131-159), `Dynamic` (:168-171).
**Signature:** `Portal(props: { mount?: Node; useShadow?: boolean; isSVG?: boolean; ref?; children })`; `Dynamic(props: { component: T | undefined } & ComponentProps<T>)`.
**Data Shape:** insert/spread/getNextElement/SVGElements all come from dom-expressions (NOT this repo — same external contract as babel). Portal returns a text-node MARKER as its JSX position placeholder.

### Decisive source
```ts
export function Portal<T extends boolean = false, S extends boolean = false>(props: {...}) {
  const { useShadow } = props,
    marker = document.createTextNode(""),
    mount = () => props.mount || document.body,
    owner = getOwner();
  let content: undefined | (() => JSX.Element);
  let hydrating = !!sharedConfig.context;
  createEffect(() => {
      // basically we backdoor into a sort of renderEffect here
      if (hydrating) (getOwner() as any).user = hydrating = false;
      content || (content = runWithOwner(owner, () => createMemo(() => props.children)));
      const el = mount();
      if (el instanceof HTMLHeadElement) { ...insert with cleanup signal... }
      else {
        const container = createElement(props.isSVG ? "g" : "div", props.isSVG),
          renderRoot = useShadow && container.attachShadow
            ? container.attachShadow({ mode: "open" })
            : container;
        Object.defineProperty(container, "_$host", {
          get() { return marker.parentNode; }, configurable: true
        });
        insert(renderRoot, content);
        el.appendChild(container);
        props.ref && (props as any).ref(container);
        onCleanup(() => el.contains(container) && el.removeChild(container));
      }
  }, undefined, { render: !hydrating });
```

**Flow:** marker text node anchors ownership position while actual DOM lives under `mount()`; children memo created ONCE under the ORIGINAL owner (`runWithOwner`) so disposal follows the usage site, not the portal target. Dynamic memoizes the component accessor then switches on typeof: functions render through untracked component call; strings create (or hydrate-claim via `getNextElement()`) a real element and `spread` props onto it.
**Invariant:** The `{ render: !hydrating }` option + manual `user` flag flip make Portal's effect behave as a render effect only when NOT hydrating. `_$host` back-reference enables event delegation retargeting to the marker's parent. In-repo DOM code is nearly ZERO by design — porting the web layer means taking dom-expressions as a unit.
**Probe:** `grep -c 'dom-expressions/src/client.js' packages/solid/web/src/client.ts` → `1`. Behavior pinned by test/rendering.spec.ts.
**Retrieve:** (re-executed against project `solid` at the same pin, 2026-08-25)
```ts
await mcp.codebase_memory.search_graph({ project: "solid", query: "Portal createDynamic spread insert marker", limit: 10 });
```

## Verdict
Adopt Portal's owner-anchored-content pattern and Dynamic's typeof dispatch. Adapt `_$host` if you lack delegation. Treat dom-expressions as an opaque dependency unless porting it wholesale (separate repo).
