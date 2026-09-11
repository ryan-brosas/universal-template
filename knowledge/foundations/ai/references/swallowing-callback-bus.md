<!-- capsule-v2 -->
# Swallowing-callback bus — how do you fan one event out to zero-or-many callbacks (each possibly in arrays) without letting a user callback kill the run?

**Source:** Vercel AI SDK Apache-2.0 `main@d25cae2722bfaed94c56d992c6df399a736db7a9`; Codebase Memory `ai`. **Question:** What is the exact contract for awaiting user callbacks during generation so that parallelism is preserved and exceptions are contained?

## notify
**Path/Symbol:** `packages/ai/src/util/notify.ts:9-19` (`notify`).
**Signature:** `notify<EVENT>({event: EVENT, callbacks?: Arrayable<Callback<EVENT> | undefined | null>}): Promise<void>` where `Arrayable<T> = T | T[]`.
**Data Shape:** Accepts a single callback, an array, or undefined/null; resolves when every callback settles; NEVER rejects.

### Decisive source
```ts
export async function notify<EVENT>(options: {
  event: EVENT;
  callbacks?: Arrayable<Callback<EVENT> | undefined | null>;
}): Promise<void> {
  await Promise.all(
    asArray(options.callbacks).map(async callback => {
      try {
        await callback?.(options.event);
      } catch {}
    }),
  );
}
```

**Flow:** `asArray` normalizes → all callbacks invoked SYNCHRONOUSLY in the same tick (ordering by array position) but awaited concurrently → per-callback try/catch means a throw becomes a resolved `undefined`. Callers (`executeToolCall` start/end, step events) always `await notify(...)`, giving "callbacks complete before the next lifecycle stage" semantics WITHOUT giving callbacks veto power.

**Invariant:** Callbacks are observers, not middleware — they cannot alter the event, abort the flow, or delay it beyond their own promise. If a host needs veto/transform behavior, that is a different primitive (cf. repair functions), never bolted onto this bus.

**Probe:** `packages/ai/src/util/notify.test.ts:136` ("should catch errors in a single callback without breaking"), `:157` (array continues past throwing member), `:181` (async rejection caught), `:90` ("should run async callbacks in parallel and await all of them").

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "notify Arrayable asArray callback", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the 8-line contract verbatim; it is the reference implementation of observer-safety for generation lifecycles.
