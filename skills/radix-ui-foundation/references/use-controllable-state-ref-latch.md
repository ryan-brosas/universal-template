<!-- capsule-v2 -->
# useControllableState ref latch — how do you support controlled AND uncontrolled modes without stale onChange or flip-flopping owners?

**Source:** radix-ui/primitives MIT `main@f7ecd5ab16f5e1e820eb5786a1419a98a2d594ae`; Codebase Memory `ext-ui-radix-ui`. **Question:** Where does state live in each mode, when does onChange fire, and how do onChange callbacks stay fresh?

## Connected graph-selected seam
**Path/Symbol:** `packages/react/use-controllable-state/src/use-controllable-state.tsx:useControllableState` (:17-76), `useUncontrolledState` (:78-103), insertion-effect ref refresh (:89-92), dev-mode flip warning (:29-46).
**Signature:** `useControllableState<T>({prop?, defaultProp, onChange?, caller?}) → [T, Dispatch<SetStateAction<T>>]`.
**Data Shape:** controlled mode: NO internal state — value IS prop; uncontrolled: useState(defaultProp) with prevValueRef ledger; onChangeRef refreshed in useInsertionEffect (obfuscated property access `' useInsertionEffect '.trim().toString()` defeats bundler renaming; falls back to useLayoutEffect).

### Decisive source
```ts
const setValue = React.useCallback<SetStateFn<T>>(
  (nextValue) => {
    if (isControlled) {
      const value = isFunction(nextValue) ? nextValue(prop) : nextValue;
      if (value !== prop) {
        onChangeRef.current?.(value);   // notify only; owner decides
      }
    } else {
      setUncontrolledProp(nextValue);
    }
  },
  [isControlled, prop, setUncontrolledProp, onChangeRef],
);
...
useInsertionEffect(() => { onChangeRef.current = onChange; }, [onChange]);
```

**Flow:** render picks value source by `prop !== undefined` → setter in controlled mode resolves updater functions against the CURRENT prop and fires onChange WITHOUT storing anything (the owner's re-render is the commit) → uncontrolled mode defers onChange to a passive effect comparing prevValueRef so setState batching never double-notifies → dev-only effect warns on controlled↔uncontrolled flips mid-lifetime ("Decide between using a controlled or uncontrolled value for the lifetime of the component").
**Invariant:** the ref-latch (insertion-effect-refreshed onChangeRef) is what keeps the setValue callback stable while accepting new closures every render — porters who put onChange straight into useCallback deps produce identity churn that tears memoized consumers; controlled mode must NEVER write local state or you get desync loops with strict owners.
**Probe:** byte-exact anchors: `bash -c "cd $REFERENCE_ROOT/external/ui-radix-ui && grep -nF 'Components should not switch from controlled to uncontrolled' packages/react/use-controllable-state/src/use-controllable-state.tsx"` (:40) and `grep -nF 'onChangeRef.current = onChange;' packages/react/use-controllable-state/src/use-controllable-state.tsx"` (:91). Consumer behavior pinned by select form-reset suites (uncontrolled vs controlled branches :276-390 drive both paths).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-radix-ui", query: "useControllableState controlled uncontrolled onChange", limit: 10 });
```

## Verdict
Adopt verbatim including the obfuscated useInsertionEffect access; adapt the warning text/caller naming to your DX conventions; omit nothing — this hook is fully portable. No isolated spec file at pin; verified via whole-file read + consumer test coverage.
