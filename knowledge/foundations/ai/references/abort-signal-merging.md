<!-- capsule-v2 -->
# Abort-signal merging — how do user aborts and timeout timers become one signal without inventing timers that were never configured?

**Source:** Vercel AI SDK Apache-2.0 `main@d25cae2722bfaed94c56d992c6df399a736db7a9`; Codebase Memory `ai`. **Question:** How do you combine N abort sources (signals + millisecond timeouts) into one signal while preserving "no sources ⇒ no signal"?

## mergeAbortSignals
**Path/Symbol:** `packages/ai/src/util/merge-abort-signals.ts:13-25` (`mergeAbortSignals`).
**Signature:** `mergeAbortSignals(...signals: (AbortSignal | null | undefined | number)[]): AbortSignal | undefined`.
**Data Shape:** Accepts signals and bare timeout numbers in any mix; nullish entries ignored; returns `undefined` when nothing valid remains — callers must handle the no-restriction case instead of fabricating a never-aborting signal.

### Decisive source
```ts
const validSignals = filterNullable(...signals).map(signal =>
  signal instanceof AbortSignal ? signal : AbortSignal.timeout(signal),
);

return validSignals.length === 0
  ? undefined
  : validSignals.length === 1
    ? validSignals[0]
    : AbortSignal.any(validSignals);
```

**Flow:** filter → coerce numbers via `AbortSignal.timeout(ms)` → 0 sources ⇒ `undefined`; 1 source ⇒ returned AS-IS (identity, so an already-aborted input's reason is preserved); ≥2 ⇒ `AbortSignal.any`. The first source to fire supplies the abort reason (tests pin both Error and string reasons).

**Invariant:** `undefined` return is meaningful — it means "no abort constraint", and `executeToolCall`'s test asserts the tool then receives literally `undefined` rather than a dummy signal. Wrapping a lone user signal in `AbortSignal.any` would still work but loses identity/reason fidelity; the ladder preserves it.

**Probe:** `packages/ai/src/util/merge-abort-signals.test.ts:84` ("should return undefined when no signals provided"), `:90` (only null/undefined), `:36/:48` (reason preserved from triggering source), `:69` (first already-aborted wins), `:96` (numeric input becomes a timeout signal).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "mergeAbortSignals AbortSignal.any", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three-ladder return (`undefined | identity | any`). Adapt coercion rules if your runtime lacks `AbortSignal.any` (polyfill or manual listener fan-in).
