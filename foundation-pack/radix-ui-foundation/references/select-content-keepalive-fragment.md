<!-- capsule-v2 -->
# Select content keep-alive — how do items stay "mounted" for data gathering while the popup is closed or animating out?

**Source:** radix-ui/primitives MIT `main@f7ecd5ab16f5e1e820eb5786a1419a98a2d594ae`; Codebase Memory `ext-ui-radix-ui`. **Question:** How does Select gather item data (native options, selected textValue) while closed without rendering a visible popup?

## Connected graph-selected seam
**Path/Symbol:** `packages/react/select/src/select.tsx:SelectContent` (:522-551), `SelectContentFragment` (:562-577), Presence gate (:540-548), SSR-safe fragment state (:527-532).
**Signature:** `SelectContent` branches on Presence render-prop: present ⇒ `<SelectContentImpl>`; absent ⇒ `<SelectContentFragment fragment={fragment}>` portalled into a DETACHED DocumentFragment.
**Data Shape:** `fragment` held in state, set in useLayoutEffect (`DocumentFragment` doesn't exist on server); Fragment subtree keeps Collection.ItemSlot registrations and ItemText native-option effects ALIVE.

### Decisive source
```tsx
// The `Select` items collect their data (e.g. to build the native `option`s
// and to display the selected value) by mounting their children. We keep
// them mounted in a detached fragment whenever the content isn't present so
// that this data stays up to date even while the select is closed (or
// animating out).
return (
  <Presence present={forceMount || context.open}>
    {({ present }) =>
      present ? (
        <SelectContentImpl {...contentProps} ref={forwardedRef} />
      ) : (
        <SelectContentFragment {...contentProps} fragment={fragment} />
      )
    }
  </Presence>
);
```

**Flow:** close → Presence suspends (exit animation may hold it in unmountSuspended) → when truly unmounted, children re-home into the off-document fragment via createPortal(fragment) → item layout effects still ran, so provider state holds native options + selected textValue → trigger stays accurate while closed → open re-renders into the real positioned impl. The fragment branch renders null until after first client layout effect (SSR-safe).
**Invariant:** naive ports unmount items when closed and LOSE the value display + form options (the bubble input empties); the detached-subtree trick requires that all data-gathering happen in effects/refs rather than DOM-connected APIs (getBoundingClientRect etc. return zeros in a fragment — which is fine because nothing measures while closed). aria-hidden on the closed content is unnecessary precisely because a DocumentFragment is not rendered.
**Probe:** direct tests `packages/react/select/src/select.test.tsx` — `should reference a non-existent element while closed` vs `reference the rendered content while open` (:57-75, aria-controls contract across this transition) and ref-stability suite (:259-268). Byte-exact anchor: `bash -c "cd /mnt/hdd/utopia/inspo/external/ui-radix-ui && grep -nF '<SelectContentFragment {...contentProps} fragment={fragment} />' packages/react/select/src/select.tsx"` (:545).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-radix-ui", query: "SelectContentImpl Presence fragment portal", limit: 10 });
```

## Verdict
Adopt the two-branch Presence pattern for any component whose CHILDREN carry side-channel data registration; adapt by swapping Presence for your exit-animation keeper; omit the SSR fragment dance only for client-only hosts (record it). Pinned by upstream aria-controls + ref-stability tests at this pin.
