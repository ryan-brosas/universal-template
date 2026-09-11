<!-- capsule-v2 -->
# AsyncQueue handoff primitive — how do a background producer and an async-iteration consumer rendezvous without races on close?

**Source:** veda-ts MIT `master@c3c69f2c340ec81ada8ea974076ce5bbaf5ccbc6` (v0.75.9); Codebase Memory `veda`. **Question:** What is the minimal queue contract that lets `runDeepThink`'s event pump push from a promise while the stage machine iterates, with correct behavior for push-after-close, error injection, and buffered drain?

## Waiter-first async iterator
**Path/Symbol:** `src/util/queue.ts` : `AsyncQueue<T>` (:1-70, whole file); consumed by `src/pipelines/deep-think.ts` as its event/checkpoint channel.
**Signature:** `class AsyncQueue<T> implements AsyncIterable<T>` — methods `push(item)`, `done()`, `fail(err)`, `[Symbol.asyncIterator]`.
**Data Shape:** internal `queue: T[]`, `waiters: ((r: IteratorResult<T>) => void)[]`, `closed: boolean`, `error: Error | null`.

### Decisive source
```ts
push(item: T): void {
    if (this.closed) return;                    // post-close pushes are SILENTLY dropped
    const waiter = this.waiters.shift();
    if (waiter) waiter({ value: item, done: false });   // waiter-first: no buffering when a consumer waits
    else this.queue.push(item);
}
fail(err: Error): void {
    if (this.closed) return;
    this.error = err;                           // stored, NOT thrown to waiters now
    this.closed = true;
    while (this.waiters.length > 0) {
      const waiter = this.waiters.shift()!;
      waiter({ value: undefined as any, done: true });   // released as DONE; throw happens at next pull
    }
}
async *[Symbol.asyncIterator](): AsyncIterator<T> {
    while (true) {
      if (this.error) throw this.error;         // error surfaces at ITERATION time
      if (this.queue.length > 0) { yield this.queue.shift()!; continue; }   // drain beats close
      if (this.closed) return;
      const result = await new Promise<IteratorResult<T>>(resolve => this.waiters.push(resolve));
      if (this.error) throw this.error;
      if (result.done) return;
      yield result.value;
    }
}
```

**Flow:** every mutation is idempotent after `close` (`done()`/`fail()` both set closed once; later pushes vanish) → producer-consumer handoff is waiter-first so a waiting consumer receives items by direct resolve, zero-copy → consumer loop drains ALL buffered items before honoring close ("drain beats close" ordering in the iterator) → `fail` stores the error and releases waiters with done:true, deferring the THROW to the iterator's next checkpoint so cancellation never loses already-queued events.
**Invariant:** items pushed before `done()` are always delivered even if the consumer wasn't yet pulling; an errored queue never delivers a partial item silently — it throws exactly once at iteration; double-close is a no-op. This is what makes deep-think's fire-and-forget producer safe against the stage machine's early exits.
**Probe:** no dedicated upstream suite — exercised via `tests/core/ensemble-retry.test.ts` + deep-think tests at pin. Deterministic pin: `grep -n "waiter-first\|if (this.closed) return" src/util/queue.ts` shows both guards. Run: `bun test tests/core/ensemble-retry.test.ts`.
**Retrieve:**
```
codebase-memory-mcp cli search_graph '{"project":"veda","query":"AsyncQueue push done fail","limit":5,"detail":"ids"}'
```
→ resolves `veda.src.util.queue.AsyncQueue Class src/util/queue.ts 1-70`.

## Verdict
Adopt whole (~70 lines): waiter-first delivery, silent post-close push, drain-before-close iteration, deferred error throw. Adapt nothing behavioral; rename only. Coverage caveat: no direct unit test file — port with your own concurrency test.
