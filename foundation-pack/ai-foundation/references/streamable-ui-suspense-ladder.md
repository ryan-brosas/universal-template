<!-- capsule-v2 -->
# Streamable UI suspense ladder — how do React nodes stream over RSC as a recursive Suspense chain?

**Source:** Vercel AI SDK Apache-2.0 `main@d25cae2722bfaed94c56d992c6df399a736db7a9`; Codebase Memory `ai`. **Question:** How does `createStreamableUI().update()` reach the client, and what do append/done/error mean at the RSC payload level?

## createStreamableUI + createSuspendedChunk
**Path/Symbol:** `packages/rsc/src/streamable-ui/create-streamable-ui.tsx` (:55-148); renderer `streamable-ui/create-suspended-chunk.tsx` (:5-84); driver `stream-ui/stream-ui.tsx:streamUI` (:98-431).
**Signature:** wrapper `{value: ReactNode, update(node), append(node), error(e), done(node?)}`; chunk `{done:false, value, next: Promise<Chunk>, append?} | {done:true, value}`.
**Data Shape:** `value` is a single React element tree — an `<R c n>` component chain where each row awaits its `next` promise and renders the awaited row inside `<Suspense fallback={row.value}>`.

### Decisive source
```tsx
// the recursive row (single-letter names shrink the RSC payload):
const chunk = await next;
if (chunk.done) return chunk.value;
if (chunk.append)
  return <>{current}<Suspense fallback={chunk.value}><R c={chunk.value} n={chunk.next}/></Suspense></>;
return <Suspense fallback={chunk.value}><R c={chunk.value} n={chunk.next}/></Suspense>;
// update(): resolve the CURRENT promise with {done:false, next}, then rebind
// resolve/reject to the new resolvable — the client falls into the next row:
resolve({ value: currentValue, done: false, next: resolvable.promise });
resolve = resolvable.resolve; reject = resolvable.reject;
// referential no-op guard on update ONLY (append always emits):
if (value === currentValue) { warnUnclosedStream(); return streamable; }
```

**Flow:** create arms dev-only hanging warning + initial `<Suspense fallback={initialValue}>` → update resolves current row with next-promise (client shows previous subtree until the new node suspends in) → append wraps the NEW chain beside the frozen old one (`current` stays rendered; further appends nest outward) → error rejects the pending promise so the nearest client ERROR BOUNDARY catches it (streamUI deliberately does NOT throw server-side :419-423) → done(final?) resolves terminal `{done:true}`. streamUI drives it: text deltas call `render(textRender)` per delta; the FIRST tool-call becomes `isLastCall:true` and its generator/async-generator yields stream successive nodes; renders serialize through a `finished` PROMISE CHAIN (:238-240) so overlapping text/tool renders cannot interleave out of order; no-tool-call streams finish with one final `done:true` text render.
**Invariant:** update() after done() throws ('UI stream is already closed'); referential-equal updates are dropped but appends never are. The finished-chain serialization is load-bearing for generator renderers — awaiting each render before the next preserves node ordering under concurrent text+tool streams.
**Probe:** `packages/rsc/src/stream-ui/stream-ui.ui.test.tsx:122/:132` (text + function-rendered UI), `:189/:213` (tool-call results incl. generator render), `packages/rsc/src/streamable-ui/create-streamable-ui.ui.test.tsx` (wrapper semantics).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "createStreamableUI createSuspendedChunk streamUI render finished", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the recursive-Suspense encoding, promise-rebinding update protocol, append-vs-update semantics, and the finished-chain render serializer. Adapt fallback strategy to your framework. Omit nothing behavioral.
