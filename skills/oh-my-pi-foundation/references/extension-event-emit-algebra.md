<!-- capsule-v2 -->
# Extension event emit algebra — what are the reduction rules for broadcasting one event to many third-party handlers?

**Source:** oh-my-pi (MIT) `main@2b66ee69f249`; Codebase Memory `oh-my-pi`. **Question:** When N extensions subscribe to an event, in what order do handlers run, whose result wins, when do you short-circuit, and which errors continue vs throw?

## Connected graph-selected seam
**Path/Symbol:** `packages/coding-agent/src/extensibility/extensions/runner.ts:ExtensionRunner.emit` (:1334-1395), `emitToolResult` (:1397-1438); twin plane `hooks/runner.ts:HookRunner.emit` (:270-319), `emitContext` chaining (:358-386), `emitBeforeAgentStart` first-wins (:392-424).
**Signature:** `emit<TEvent>(event): Promise<Result | undefined>` — sequential per extension, per handler registration order.
**Data Shape:** handlers stored `Map<eventType, HandlerFn[]>` per extension/hook; result union keyed by event type.

### Decisive source
```ts
// Lazy context allocation: streaming sessions emit message_update / tool_execution_*
// per delta with usually NO extension subscribed; building ctx for a zero-handler
// event is pure waste (and skips all Promise.race machinery).
let ctx: ExtensionContext | undefined;
for (const ext of this.extensions) {
	const handlers = ext.handlers.get(event.type);
	if (!handlers || handlers.length === 0) continue;
	ctx ??= this.createContext();
	for (const handler of handlers) {
		const handlerResult = await this.#runHandlerWithTimeout(handler, event, ctx, ext, handlerTimeoutForEvent(event.type));
		if (this.#isSessionBeforeEvent(event) && handlerResult) {
			result = handlerResult as SessionBeforeEventResult;
			if (result.cancel) return result;   // cancel short-circuits remaining hooks
		}
```
**Flow (the reduction table):** session_before_* → LAST truthy result wins, `.cancel === true` short-circuits; `session.compacting` / `session_stop` → last wins, stop short-circuits on `continue===true || decision==="block"` WITH non-empty continuation context; `tool_result` (extension plane, emitToolResult) → CHAINED: each handler receives the previous modifications via a mutated currentEvent, returns undefined if nobody modified; `before_agent_start` → FIRST message wins; `context` (both planes) → PIPELINE: each handler gets previous output messages; `session_shutdown` → all handlers concurrently, no result. Errors: extension-plane dispatch catches to onError and continues; hook-plane `HookRunner.emit` same, but hook-plane `emitToolCall` deliberately has **no timeout** ("user prompts can take as long as needed") and **throws** so the caller blocks on failure — while the extension-plane `emitToolCall` has the 30s budget and converts timeout/error into fail-closed `{ block: true }`.
**Invariant:** handler order is deterministic (extension path order × registration order); a handler that returns nothing never clobbers an earlier result except where the rule is chained/last-wins by design.
**Probe:** direct-test seam: `test/compaction-hooks.test.ts` + `test/extensibility/extension-load-notifications.test.ts` exist; anchor-greps at pin: "cancel" short-circuit line runner.ts :1374, "currentEvent.content = handlerResult.content" :1417, hooks "if (result.cancel)" runner.ts(hooks) :296.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "emitToolResult emitContext before_agent_start", limit: 10 });
```

## Verdict
Adopt: the reduction table + lazy ctx allocation + deterministic ordering. Adapt: event-type names to your domain. Omit: the exact settings-driven timeout key wiring (see extension-handler-timeout-budget capsule).
