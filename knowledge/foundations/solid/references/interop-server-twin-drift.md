<!-- capsule-v2 -->
# interop server-twin drift — what survives SSR compile-out in the observable/from bridges, and what silently narrows?

**Source:** SolidJS solid MIT `main@f47845f9cc16ecbb316aa6560c7161f45af9a3d8`; Codebase Memory `solid`. **Question:** If a porter ships the interop bridges through the server build, which contracts hold byte-for-byte and which change shape?

## Connected graph-selected seam
**Path/Symbol:** `packages/solid/src/server/reactive.ts:observable` (:308–343), `:from` (:345–364), `:enableExternalSource` (:366); client counterparts in `packages/solid/src/reactive/observable.ts` (:46–85, :93–106).
**Signature:** server `from<T>(producer: Producer<T>): Accessor<T>` — **one overload, no `initialValue` parameter**; server `ObservableObserver<T>.next` is required (`next: (v:T)=>void`, not optional).
**Data Shape:** same `Producer` union; server signal starts at `undefined` and is cast `as [Accessor<T>, Setter<T>]`.

### Decisive source
```ts
// server/reactive.ts:352-355 — initialValue overload is gone, start is hardwired
const [s, set] = createSignal<T | undefined>(undefined, { equals: false }) as [
  Accessor<T>,
  Setter<T>
];
```
and (:366):
```ts
export function enableExternalSource(factory: any) {}
```

**Flow:** the server twin re-implements the full client bridge on top of its own createRoot/createEffect/createSignal/onCleanup — `observable()` is line-for-line identical (same TypeError gate, same untracked handler, same owner-tied disposal, same inline `Symbol.observable || "@@observable"`), so Rx interop keeps working under SSR.
**Invariant / drift list:** (1) `observable()` — no drift; (2) `from()` — the `initialValue` overload disappears and readers see `undefined` until first push; (3) `ObservableObserver.next` becomes required at type level only; (4) `enableExternalSource` degrades to a no-op stub, whereas the client version (see external-source-bridge) wires the composable factory chain. Code calling the two-arg `from(producer, init)` type-checks against the client entry and silently loses its seed under the server entry.
**Probe:** graph evidence: `get_code_snippet("solid.packages.solid.src.server.reactive.observable")` returned the byte-identical body (:308–343); direct read of `server/reactive.ts:300–369` confirms the narrowed `from`. No dedicated spec file covers `server/reactive.ts` bridges — coverage caveat: behavior claims rest on direct source reads, not tests.

## Get live surrounding code
**Retrieve:** executed BM25 query ranks `server.reactive.subscribe` (:310–338), `server.reactive.from` (:345–364) and `server.reactive.[Symbol.observable || "@@observable"]` alongside the client originals.
```ts
await mcp.codebase_memory.search_graph({ project: "solid", query: "observable from interop bridge subscribe", limit: 10 });
```

## Verdict
Adopt "interop built only from kernel primitives survives compile-out" as the porting rule. Adapt any consumer that relies on `from(producer, initialValue)` or external-source factories under your server entry — restore those two narrowings explicitly. Omit assuming test parity: this plane is untested upstream; cite source lines only. This capsule refines ssr-shadow-kernel's deletion-list story with the one place the twin stays *functional* rather than frozen.
