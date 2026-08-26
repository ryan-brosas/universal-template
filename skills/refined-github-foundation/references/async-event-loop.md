<!-- capsule-v2 -->
# Async Event Loop — how do you consume a DOM event stream inside a `for await` loop that cleans up on abort?

**Source:** refined-github MIT `main@3bbe6088fe301d0d5cf1ae751a49307005762a68`; Codebase Memory `refined-github`. **Question:** What is the correct async-generator shape for events — queue-buffered, abort-safe, listener-removed even on early exit?

## Connected graph-selected seam
**Path/Symbol:** `source/helpers/event-listener-loop.ts:` `createEventIterator` (:1–36). Direct test: `source/helpers/event-listener-loop.test.ts`.
**Signature:** `createEventIterator<T extends Event>(element: EventTarget, eventName: string, {signal?, once?}): AsyncGenerator<T>` (exported default).
**Data Shape:** internal `queue: T[]` + a swap-on-resolve deferred (`Promise.withResolvers<void>()`) — every arriving event pushes to the queue and resolves the CURRENT deferred, then immediately installs a fresh one.

### Decisive source
```ts
const handler = (event: Event): void => {
	queue.push(event);
	deferred.resolve();
	deferred = Promise.withResolvers<void>();   // re-arm for the next wait
};
try {
	element.addEventListener(eventName, handler, {once});
	while (!signal?.aborted) {
		if (queue.length === 0) await deferred.promise;
		yield queue.shift()!;
		if (once) break;
	}
} finally {
	element.removeEventListener(eventName, handler);
}
```

**Flow:** addEventListener → loop { empty queue? park on deferred; else yield next queued event } → generator return/break/abort lands in `finally`, which removes the listener. Events fired while the consumer body is still awaiting are buffered in `queue`, not dropped.
**Invariant:** cleanup lives in `finally` so ANY exit path (break, throw, `.return()` on the generator, aborted signal) detaches the listener — porting it as a bare `while(true){await oneEvent()}` leaks a listener per iteration. The deferred-swap (resolve-then-replace) is what avoids missing the signal between `await` and wakeup; checking `signal?.aborted` at loop top handles the race where abort fires while parked.
**Probe:** `source/helpers/event-listener-loop.test.ts` — `describe('createEventIterator')` :5 with three `it`s: yields events :6, STOPS on signal abort :19, multiple events :40 (the helper's sole export is `export default createEventIterator`, event-listener-loop.ts:38) — pins consumption semantics incl. abort.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "refined-github", query: "createEventIterator event listener async generator", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt verbatim (~36 lines, zero deps) whenever a feature needs sequential event processing with lifecycle teardown. Adapt event target/name typing. Nothing to omit. Direct unit test present.
