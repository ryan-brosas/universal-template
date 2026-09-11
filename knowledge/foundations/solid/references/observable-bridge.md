<!-- capsule-v2 -->
# observable() bridge — how does a Solid accessor become a spec-shaped ES Observable without leaking reactive writes?

**Source:** SolidJS solid MIT `main@f47845f9cc16ecbb316aa6560c7161f45af9a3d8`; Codebase Memory `solid`. **Question:** What exact lifecycle does each `subscribe()` create, and who disposes it?

## Connected graph-selected seam
**Path/Symbol:** `packages/solid/src/reactive/observable.ts:observable` (:46–85).
**Signature:** `observable<T>(input: Accessor<T>): Observable<T>`; `subscribe(observer: ObservableObserver<T>) → { unsubscribe(): void }`.
**Data Shape:** `ObservableObserver<T>` = bare function **or** `{ next?, error?, complete? }`; only `next` is ever wired. The returned object carries `[Symbol.observable || "@@observable"](){ return this; }` computed inline (PR #1118 comment: interop without polyfilling `Symbol.observable` or caching it in an intermediary).

### Decisive source
```ts
const handler =
  typeof observer === "function" ? observer : observer.next && observer.next.bind(observer);

if (!handler) {
  return { unsubscribe() {} };          // no root, no effect — dead subscription
}

const dispose = createRoot(disposer => {
  createEffect(() => {
    const v = input();
    untrack(() => handler(v));           // observer side-effects stay untracked
  });
  return disposer;
});

if (getOwner()) onCleanup(dispose);      // scope-tied auto-disposal
```

**Flow:** validate (`!(observer instanceof Object) || observer == null` → `TypeError`) → extract handler (function used as-is; object gets bound `.next` only) → no handler ⇒ no-op unsubscribe with zero machinery → else fresh `createRoot` + `createEffect` per subscribe; effect runs immediately so the current value is delivered synchronously → if an owner exists, `onCleanup(dispose)` binds teardown to that scope; manual `unsubscribe()` calls the same `dispose`.
**Invariant:** every subscription owns exactly one root+effect pair; observer callbacks must never become tracked dependencies (the `untrack`). `error`/`complete` are accepted by type but never invoked by this bridge.
**Probe:** `packages/solid/test/observable.spec.ts` — "to observable" pins sync initial delivery inside `createRoot`; "preserve the observer's next binding" pins `.bind(observer)`; "throws TypeError on non-object"; "observable unsubscribe" pins post-unsubscribe silence.

## Get live surrounding code
**Retrieve:** BM25 query `"observable from interop bridge subscribe"` on project `solid` rank-orders `reactive.observable.subscribe`, `.from`, and the server twins in `server/reactive.ts` first (executed 2026-08-25, generation 2026-08-25T20:12:15Z).
```ts
await mcp.codebase_memory.search_graph({ project: "solid", query: "observable from interop bridge subscribe", limit: 10 });
```

## Verdict
Adopt per-subscribe root+effect ownership with owner-tied `onCleanup` disposal and the untracked-handler rule. Adapt the TypeError text/symbol fallback to host conventions. Omit nothing structural — but note the server twin is byte-identical here (see interop-server-twin-drift), so this contract ports unchanged across SSR.
