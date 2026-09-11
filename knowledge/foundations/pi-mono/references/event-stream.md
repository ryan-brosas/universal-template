<!-- capsule-v2 -->
# EventStream kernel — how do I expose a long-running operation as a typed single-consumer async event stream whose final result is also independently awaitable?

**Source:** pi-mono MIT `main@80e62761f7251a104f1b21d9c73920c720f0ec00`; Codebase Memory `pi-mono`. **Question:** one contract for streaming progress events while keeping the terminal value awaitable without consuming the stream.

## Single-consumer queue + waiter stream
**Path/Symbol:** `packages/ai/src/utils/event-stream.ts:class EventStream<T, R = T>` (lines 4-67); `AssistantMessageEventStream` (69-83); `createAssistantMessageEventStream` (86-88).
**Signature:** `constructor(isComplete: (event: T) => boolean, extractResult: (event: T) => R)`; `push(event: T): void`; `end(result?: R): void`; `[Symbol.asyncIterator](): AsyncIterator<T>`; `result(): Promise<R>`.
**Data Shape:** private `queue: T[]` + `waiting: ((r: IteratorResult<T>) => void)[]` + `done` flag; `finalResultPromise` resolved by the completing event or by `end(result)`. Generic over event type `T` and final result `R`; `agentLoop` instantiates `EventStream<AgentEvent, AgentMessage[]>` with `isComplete = (e) => e.type === "agent_end"`.

### Decisive source
```ts
push(event: T): void {
	if (this.done) return;
	if (this.isComplete(event)) {
		this.done = true;
		this.resolveFinalResult(this.extractResult(event));
	}
	const waiter = this.waiting.shift();
	if (waiter) waiter({ value: event, done: false });
	else this.queue.push(event);
}
async *[Symbol.asyncIterator](): AsyncIterator<T> {
	while (true) {
		if (this.queue.length > 0) yield this.queue.shift()!;
		else if (this.done) return;
		else {
			const result = await new Promise<IteratorResult<T>>((resolve) => this.waiting.push(resolve));
			if (result.done) return;
			yield result.value;
		}
	}
}
```

**Flow:** producer calls `push` → if the event satisfies `isComplete`, mark done and resolve the final-result promise from that same event → deliver to the single waiting consumer or enqueue → consumer drains the FIFO backlog first, then awaits new waiters → `end(result?)` marks done and flushes waiters with `{done:true}` → `result()` returns the independent promise at any time.
**Invariant:** exactly one consumer; events are yielded in push order, never reordered, never dropped before `done`. Pushes after `done` are silently discarded. `result()` must not require iterating the stream, and iteration must not require calling `result()`. In `AssistantMessageEventStream` an `error` event RESOLVES (not rejects) the final promise with the error value — consumers branch on message shape, not try/catch.
**Probe:** no dedicated unit suite exists in `packages/ai` (recorded caveat). Behavioral probe executed 2026-08-25: `packages/agent/test/agent-loop.test.ts` passed within the 3-file / 47-test vitest run; it drives `createAgentStream()` end-to-end (`isComplete = agent_end`, result = final `AgentMessage[]`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-mono", name_pattern: "EventStream", file_pattern: "packages/ai/src/utils/event-stream.ts" });
```

## Verdict
Adopt the queue+waiter dual surface (iterable events plus an independent result promise) and drop-after-done discipline. Adapt `T`/`R` to your event vocabulary and completion predicate. Omit the `AssistantMessageEventStream`-specific done/error→message mapping unless porting pi’s provider plane. Caveat: cited file is graph-clean (`no_recorded_issue`) but has no dedicated direct suite — treat agent-loop tests as the behavioral anchor.
