<!-- capsule-v2 -->
# Top-layer stack machine — which open component owns Escape and outside-click when Dialogs, Menus, and Popovers nest?

**Source:** Headless UI MIT `main@eea57cf46fd6767ed1059012f7073b88eb159fba`; Codebase Memory `ext-ui-headlessui`. **Question:** How is "am I the topmost interactive layer" computed across components that don't share a React tree?

## StackMachine + DefaultMap scopes + useIsTopLayer
**Path/Symbol:** `packages/@headlessui-react/src/machines/stack-machine.ts:22-72`; `packages/@headlessui-react/src/utils/default-map.ts:1-16`; `packages/@headlessui-react/src/hooks/use-is-top-layer.ts:29-66`.
**Signature:** `stackMachines: DefaultMap<Scope, StackMachine>` with `Scope = string | null`; actions `push(id)/pop(id)`; selectors `isTop(state,id)`, `inStack(state,id)`; hook `useIsTopLayer(enabled: boolean, scope: string | null): boolean`.
**Data Shape:** state is `{ stack: Id[] }`; scope `null` is the GLOBAL machine (Dialogs, Listbox close-on-push); `'focus-trap#tab-lock'`, `'focus-trap#initial-focus'`, `'scroll-lock'`, `'inert-others'` scope separate stacks per feature.

### Decisive source
```ts
[ActionTypes.Push](state, action) {
  let idx = state.stack.indexOf(action.id)
  if (idx !== -1) {                       // already present: MOVE to top (no double entry!)
    let copy = state.stack.slice()
    copy.splice(idx, 1)
    copy.push(id)
    return { ...state, stack: copy }
  }
  return { ...state, stack: [...state.stack, action.id] }
}
[ActionTypes.Pop](state, action) {
  let idx = state.stack.indexOf(action.id)
  if (idx === -1) return state            // not in stack: silent no-op
  ...
}
// useIsTopLayer optimistic window:
if (!enabled) return false
if (onStack) return isTop
return true   // enabled but effect hasn't pushed yet — assume we ARE top this render
```

**Flow:** every consumer pushes its `useId()` while enabled (iso-morphic effect) and pops on cleanup → `isTop` compares last element → consumers gate Escape/outside-click/scroll-lock/inert on their own topness. ListboxMachine additionally SUBSCRIBES to the global machine: any Push where it isn't top force-closes it.
**Invariant:** push of an existing id MOVES it to the top rather than duplicating (verified live: `[d1,m1]+push(d1)=[m1,d1]`); pop is idempotent-safe with NO refcount — a component that pushes twice and pops once still loses its slot (live probe: double-push single-pop → `[]`); the enabled-but-not-yet-pushed window returns TRUE optimistically so the first render can already claim handlers.
**Probe:** live `/tmp/hui-pass1-probe/probe-stack-inert-overflow.mjs` pins move-to-top, ghost-pop no-op, and no-refcount semantics. Direct behavior: dialog.test.tsx nested-layer suites via `stackMachines.get(null)`; graph probe `search_graph --query "stackMachines DefaultMap scope"` resolves Scope Type + DefaultMap nodes line-exact.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-headlessui", query: "DefaultMap scope", name_pattern: "DefaultMap", limit: 5 });
```

## Verdict
Adopt the reducer exactly (move-not-duplicate push, silent pop, optimistic true); adapt scoping to your DI/context system but KEEP one global scope for cross-component arbitration; omit per-feature scopes only if your host never stacks two traps. Caveat: `overflows`/`stackMachines` module Variables are invisible to BM25 name search — retrieve via DefaultMap/PUSH symbols.
