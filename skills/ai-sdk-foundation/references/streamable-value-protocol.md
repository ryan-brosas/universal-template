<!-- capsule-v2 -->
# Streamable value protocol — how does a server value stream updates to the client as a promise chain with string patches?

**Source:** Vercel AI SDK Apache-2.0 `main@d25cae2722bfaed94c56d992c6df399a736db7a9`; Codebase Memory `ai`. **Question:** What is the wire shape of `createStreamableValue().value`, and what must reader and writer each guarantee?

## createStreamableValue / readStreamableValue
**Path/Symbol:** `packages/rsc/src/streamable-value/create-streamable-value.ts` (:14-295); reader `read-streamable-value.tsx:readStreamableValue` (:34-113); guard `is-streamable-value.ts` (duck-type on `STREAMABLE_VALUE_TYPE`).
**Signature:** wrapper `{value, update(v), append(v), error(e), done(v?), [LOCK]: boolean}`; `value` emits `StreamableValue = {type?, curr?, diff?: [0, suffix], next?: Promise<StreamableValue>, error?}`.
**Data Shape:** patch tuple `[0, suffix]` = "append to string"; absence of `diff` = full replacement via `curr`; `next` chains to the following snapshot; terminal row has no `next`.

### Decisive source
```ts
// update(): resolve the PREVIOUS resolvable with a wrapped snapshot whose .next
// points at the NEW promise — readers walk the chain:
const resolvePrevious = resolvable.resolve;
resolvable = createResolvablePromise();
updateValueStates(value);            // computes patch vs currentValue
currentPromise = resolvable.promise;
resolvePrevious(createWrapped());    // {diff} or {curr}, plus next: currentPromise
// payload minimization — only prefix-extends become patches:
function updateValueStates(value) {
  currentPatchValue = undefined;
  if (typeof value === 'string' && typeof currentValue === 'string'
      && value.startsWith(currentValue))
    currentPatchValue = [0, value.slice(currentValue.length)];
  currentValue = value;
}
// reader applies patches cumulatively and type-checks:
if (row.diff[0] === 0) {
  if (typeof value !== 'string') throw new Error('Invalid patch: can only append to string types. This is a bug in the AI SDK.');
  (value as string) = value + row.diff[1];
}
```

**Flow:** create → dev-only hanging-stream warning timer armed (`HANGING_STREAM_WARNING_TIME_MS`, re-armed per update, cleared on error/done) → update/append resolve the previous promise with a snapshot carrying `next` → append requires BOTH sides string and always emits `[0, delta]` → done(final?) closes (`currentPromise = undefined`, resolves last row WITHOUT `next`) → error resolves `{error}` which the reader THROWS into the consumer's for-await. Stream-sourced values lock the wrapper (`STREAMABLE_VALUE_INTERNAL_LOCK`) so user updates cannot race the pump; the pump unlocks around each internal update/append/done. The hook (`use-streamable-value.tsx`) seeds state from `.curr/.error/.next` then iterates `readStreamableValue` inside `useLayoutEffect` with cancellation + `startTransition`.
**Invariant:** every intermediate row MUST carry `next` or readers terminate early; `done()` is mandatory or clients hang in pending. Patch validity is the WRITER's invariant but the READER re-checks (string-typed append) because RSC serialization erases types. First iteration skips an undefined initial value silently (:98-106).
**Probe:** `packages/rsc/src/streamable-value/create-streamable-value.test.tsx:76` ("should be able to append strings as patch"), `:114` (mixing update/append optimizes payloads), `:150/:165` (ReadableStream source incl. JSON payloads).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "createStreamableValue readStreamableValue STREAMABLE_VALUE_TYPE diff", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the promise-chain-of-snapshots encoding, prefix-patch optimization, lock-during-pump, and the mandatory-done contract. Adapt the tuple tag to your own patch grammar. Omit nothing behavioral.
