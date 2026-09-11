<!-- capsule-v2 -->
# Open/Closed context — how does a parent Transition hand its state to children that don't receive props?

**Source:** Headless UI MIT `main@eea57cf46fd6767ed1059012f7073b88eb159fba`; Codebase Memory `ext-ui-headlessui`. **Question:** What is the bit vocabulary of the open/closed context and which consumers read it implicitly?

## OpenClosedProvider / State / useOpenClosed
**Path/Symbol:** `packages/@headlessui-react/src/internal/open-closed.tsx:6-28`; primary consumer `dialog.tsx:154-158,203-204`.
**Signature:** `enum State { Open = 1<<0, Closed = 1<<1, Closing = 1<<2, Opening = 1<<3 }`; `useOpenClosed(): State | null`; `ResetOpenClosedProvider` renders a Provider with value null.
**Data Shape:** single context slot; null means "no ancestor manages my visibility"; bits are exclusive pairs (Open|Closed) optionally OR-ed with the transitional bit.

### Decisive source
```ts
export enum State {
  Open = 1 << 0,
  Closed = 1 << 1,
  Closing = 1 << 2,
  Opening = 1 << 3,
}
// Dialog: inherit when prop omitted...
let usesOpenClosedState = useOpenClosed()
if (open === undefined && usesOpenClosedState !== null) {
  open = (usesOpenClosedState & State.Open) === State.Open
}
// ...and demote features while closing:
let isClosing = usesOpenClosedState !== null && (usesOpenClosedState & State.Closing) === State.Closing
// Dialog resets the chain for ITS children:
<ResetOpenClosedProvider> ... </ResetOpenClosedProvider>
```

**Flow:** Transition/Transitions render OpenClosedProvider with e.g. `State.Closing | State.Closed` during exit → any descendant Dialog/child component without an explicit `open` prop derives it from the bits → Closing additionally flips feature flags (inert/scroll-lock off) → Dialog wraps its subtree in ResetOpenClosedProvider so SIBLING components below don't accidentally inherit dialog state.
**Invariant:** reading is `(state & State.Open) === State.Open`, never truthiness — the transitional bits share the word; a missing provider (null) must fall through to required-props validation rather than defaulting; reset boundaries are what make nested dialogs independent.
**Probe:** direct tests: dialog.test.tsx 'static' + Transition suites exercise inherited-open behavior; composition suites (`dialog.test.tsx:614-718`) pin Transition-wrapped rendering. Deterministic bit check: `State.Closing & State.Open === 0` by construction (disjoint bit positions).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-headlessui", query: "useOpenClosed ResetOpenClosedProvider", limit: 5 });
```

## Verdict
Adopt the four-bit vocabulary + bitwise reads + reset boundary verbatim; adapt to your state library as long as the transitional bit stays separately addressable; omit Opening if your host only needs closing demotion. This is the seam that makes `<Transition><Dialog open={undefined}/></Transition>` just work.
