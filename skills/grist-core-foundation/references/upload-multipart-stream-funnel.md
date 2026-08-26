<!-- capsule-v2 -->
# Streaming multipart parse with guaranteed drain — how do you hand each file part to a handler without deadlocking or leaking the connection when the handler fails mid-stream?

**Source:** grist-core Apache-2.0 `main@b83224bbe9c88910dfeb28922df254a26f702f68`; Codebase Memory `grist-core`. **Question:** What is the correct promise topology for callback-per-part multipart parsing so backpressure, handler failure, and broken streams all settle deterministically?

## per-part drainWhenSettled + allSettled AFTER finished — never leave a part unread
**Path/Symbol:** `app/server/lib/uploads.ts` — `parseMultipartFormRequest(req, onFile, onField)` (:146–201); `drainWhenSettled` (`app/server/utils/streams.ts`:31–40).
**Signature:** `parseMultipartFormRequest(req: Request, onFile?: (file: MultipartFormFile) => Promise<void>, onField?: (name: string, value: string) => void): Promise<void>` where `MultipartFormFile = {name, contentType, stream: Readable}`.
**Data Shape:** `autoField: true` makes multiparty emit ONLY file parts on `'part'`; field parts surface via `'field'`; `finished` promise resolves on form `'close'`, rejects on form/part `'error'`.

### Decisive source
```ts
const form = new multiparty.Form({ autoField: true });
form.on("part", (part) => {
  part.on("error", (err) => rejectFinished(err));   // broken stream must unblock the caller
  // The stream needs to be drained for the request to continue. If something goes wrong
  // in the `onFile` callback, drainWhenSettled guarantees that.
  partPromises.push(drainWhenSettled(part, onFile({...}), ).catch(() => {}));
});
form.on("error", (err) => rejectFinished(err));
form.on("close", () => resolveFinished());
form.parse(req);
try {
  await finished;                                   // parse result FIRST...
} finally {
  await Promise.allSettled(partPromises);           // ...THEN every part handler settles
}
// streams.ts:
export async function drainWhenSettled<T>(stream: Readable, promise: Promise<T>): Promise<T> {
  try { return await promise; }
  finally {
    if (stream.readable) { stream.resume(); }        // consume the rest, whatever happened
    await promises.finished(stream);
  }
}
```

**Flow:** request → multiparty emits file part → `onFile` promise wrapped in `drainWhenSettled` (handler result wins; stream always drained to end) → any form-level or part-level error rejects `finished` immediately while already-started handlers still run to completion in the background → after `finished` settles either way, the finally-block waits for ALL part promises via `allSettled` so no handler is abandoned mid-write.
**Invariant:** EVERY emitted part must be fully consumed or resumed, else the HTTP connection wedges and later responses can't flush — this holds even when the caller's handler throws, which is exactly what `drainWhenSettled`'s finally clause guarantees; errors from individual handlers are deliberately swallowed at the push site (`catch(() => {})`) because the callback owns its own error semantics — the funnel only guarantees transport hygiene; `await finished` BEFORE awaiting parts matters: close fires only after all parts exist.
**Probe:** `test/server/lib/uploads.ts` has no direct suite for this function (it is exercised indirectly by DocApi form routes); deterministic probe = source assertion above + `drainWhenSettled` contract pinned at `app/server/utils/streams.ts`:31–40. Coverage caveat recorded honestly: behavior pressure for THIS capsule rests on the stream-drain invariant being load-bearing in every consumer (e.g. `/api/docs/:docId/attachments` route path), not on a unit test.
**Caveat:** runner-blocked; recorded as block, not fabricated pass.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core", query: "parseMultipartFormRequest drainWhenSettled multiparty part", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three-layer topology: reject-on-any-stream-error, drain-in-finally per part, allSettled-after-close. Adapt `MultipartFormFile` shape freely. Omit buffer-to-disk inside your own parser — delegating part storage to the parser library into a pre-made tmp dir (see `upload-multipart-admission.md`) keeps this funnel simple.
