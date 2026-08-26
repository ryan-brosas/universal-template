<!-- capsule-v2 -->
# Solid SSR shadow kernel — what does the server twin delete from the reactive kernel, and what semantics must it fake?

**Source:** SolidJS solid MIT `main@f47845f`; Codebase Memory `ext-solid`. **Question:** Which client primitives are no-ops, which are single-shot fakes, and how do effects/memos collapse to plain calls?

## server/reactive.ts: the compile-out reference
**Path/Symbol:** `packages/solid/src/server/reactive.ts` (whole file :1-394): `createSignal` (:76-86), `createComputed/createRenderEffect` (:88-99), `createEffect` (:101), `createMemo` (:109-120), `createReaction` (:103-107), `onMount` (:154).
**Signature:** same public names as `reactive/signal.ts` — this file is a DROP-IN substitute selected by package exports for SSR.
**Data Shape:** Owner tree SURVIVES (`Owner`, `createOwner`, cleanups, context) because disposal/context/error-boundaries matter server-side; only tracking and scheduling die: `getListener()` returns `null` unconditionally.

### Decisive source
```ts
export function createSignal<T>(value: T, ...): [get: () => T, set: (v) => T] {
  return [
    () => value as T,
    v => { return (value = typeof v === "function" ? (v as (prev: T) => T)(value) : v); }
  ];
}
...
export function createMemo<T>(fn: (v?: T) => T, value?: T): () => T {
  Owner = createOwner();
  let v: T;
  try { v = fn(value); } catch (err) { handleError(err); }
  finally { Owner = Owner.owner; }
  return () => v;          // ← frozen snapshot, never recomputes
}
```

**Flow:** signals become a boxed variable (setter still applies function-updaters so code paths behave identically); memos/computeds evaluate EXACTLY ONCE under an owner then freeze their return; effects/onMount/reactions are literal no-ops; batch/untrack are identity. Error handling and catchError still route through handleError with real owner chains.
**Invariant:** The porting lesson is the MINIMALITY: reactivity = Listener-tracking + queue + equality. Everything else (ownership, cleanup, context, errors) is orthogonal and must keep working without it. Any SSR port that drops the owner tree breaks cleanup/context; any port that keeps tracking pays the full runtime for nothing.
**Probe:** `grep -c 'return () => v;' packages/solid/src/server/reactive.ts` → matches createMemo's frozen snapshot return. Behavior pinned by test/server/lazy.spec.ts + rendering.spec against src/server/index.js.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-solid", query: "server reactive createMemo createSignal getListener null", limit: 10 });
```

## Verdict
Adopt as the blueprint for server builds of any reactive host. Adapt nothing conceptually — copy the deletion list. Omit nothing.
