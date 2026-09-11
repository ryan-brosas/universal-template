<!-- capsule-v2 -->
# Solid error boundaries — how does the ERROR context symbol route thrown errors up the owner chain?

**Source:** SolidJS solid MIT `main@f47845f9cc16ecbb316aa6560c7161f45af9a3d8`; Codebase Memory `solid` (pass-3 refresh from retired `ext-solid` @ identical pin). **Question:** How are errors caught from memos, effects, and nested handlers without losing the reactive graph?

## catchError / handleError / runErrors ladder
**Path/Symbol:** `packages/solid/src/reactive/signal.ts:catchError` (:1033-1045), `handleError` (:1763-1776), `runErrors` (:1755-1761), `castError` (:1750-1753); deprecated twin `onError` (:1823-1833) + `mutateContext` (:1835-1848).
**Signature:** `catchError<T>(fn: () => T, handler: (err: Error) => void): T`; `handleError(err: unknown, owner = Owner)`.
**Data Shape:** module-level `ERROR: symbol | null` (lazily created); handler lists stored at `Owner.context[ERROR]: ((err) => void)[]`; `Computation.context` is inherited from the creating Owner at `createComputation`.

### Decisive source
```ts
export function catchError<T>(fn: () => T, handler: (err: Error) => void) {
  ERROR || (ERROR = Symbol("error"));
  Owner = createComputation(undefined!, undefined, true);
  Owner.context = { ...Owner.context, [ERROR]: [handler] };
  if (Transition && Transition.running) Transition.sources.add(Owner as Memo<any>);
  try {
    return fn();
  } catch (err) {
    handleError(err);
  } finally {
    Owner = Owner.owner;      // pop the boundary owner
  }
}
...
function handleError(err: unknown, owner = Owner) {
  const fns = ERROR && owner && owner.context && owner.context[ERROR];
  const error = castError(err);
  if (!fns) throw error;
  if (Effects)
    Effects.push({ fn() { runErrors(error, fns, owner); }, state: STALE } as unknown as Computation<any>);
  else runErrors(error, fns, owner);
}
```

**Flow:** boundary creates an anonymous pure computation whose context carries `[handler]`, runs the body, pops itself in `finally`. Any later failure inside owned computations reaches `handleError`: no handler in context → rethrow; inside a batch → push a SYNTHETIC computation onto `Effects` so the handler runs after the current drain settles (never mid-update); direct call → run handlers immediately. A handler that itself throws recurses via `handleError(e, owner.owner)` — bubbling to the next parent boundary.
**Invariant:** Context is COPIED by reference into each created computation (`context: Owner ? Owner.context : null`), so child lookups walk only their own context object; that's why `onError`'s late registration needs `mutateContext` to patch already-created children ("terrible de-opt" comment). Non-Error throws are normalized by `castError` with `{ cause: err }`.
**Probe:** `grep -c 'function runErrors' packages/solid/src/reactive/signal.ts` → `1`; synthetic-effect push is the `Effects.push({ fn() { runErrors(...` site. Behavior pinned by signals.spec describe("catchError") :520-698 — "Top level", "Nested in catchError", "In initial effect", "In update effect", "In nested memo".
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "solid", query: "handleError catchError ERROR context", limit: 10 });
```

## Verdict
Adopt symbol-keyed context handler lists + deferred synthetic-effect dispatch. Adapt `castError` normalization freely. Omit the deprecated `onError` mutateContext shim unless you must support late handler registration.
