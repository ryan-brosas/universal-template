<!-- capsule-v2 -->
# Held tool completions — how does a UI settle a card whose `tool_execution_end` arrived before the streamed block created it, without repeating side effects?

**Source:** oh-my-pi (see pack SKILL.md Provenance) MIT `main@2b66ee69f2`; Codebase Memory `oh-my-pi`. **Question:** When a completion outruns its card (sync server-resolved tools, fast tools losing the microtask race), what exactly is deferred and what runs immediately?

## Orphan-completion hold + settle-on-create
**Path/Symbol:** `packages/coding-agent/src/modes/controllers/event-controller.ts:` `#orphanedToolCompletions` map (:124–134), hold gate in the end handler (:1630–1637), `#settleHeldCompletionIfPresent` (:1482–1487), three consume sites: streamed-block creation (:1156–1163), execution-start creation (:1405–1409), re-key (`#rekeyToolCard` :421–428); direct tests `packages/coding-agent/test/event-controller-cursor-todo.test.ts`.
**Signature:** `#settleHeldCompletionIfPresent(toolCallId: string, component: ToolExecutionHandle): void`.
**Data Shape:** Map keyed by call id holding the full `tool_execution_end` event; cleared with the other transcript anchors per turn.

### Decisive source
```ts
} else if (!this.#toolTimelineComponents.has(event.toolCallId)) {
	// No component yet: the async streamed-block handler lost the race
	// to this completion. Hold the result instead of dropping it. Any
	// tool can finish inside that scheduling window; user-facing side
	// effects below still run now …
	this.#orphanedToolCompletions.set(event.toolCallId, event);
}
// On ANY later component materialization:
#settleHeldCompletionIfPresent(toolCallId, component) {
	const event = this.#orphanedCompletions_get(toolCallId);
	if (!event) return;
	this.#orphanedToolCompletions.delete(toolCallId);
	this.#settleHeldCompletion(component, event);   // settles ONLY the component
}
```

**Flow:** end-event arrives with no timeline entry → side effects (failure warning, todo-panel refresh, analytics) run NOW on first arrival; only the event object is parked → when the streamed block, execution-start card, or re-keyed card appears, the held event settles it immediately so it never animates forever and never pins transcript retirement. The pass-1 fix scoped this to the `todo` tool; this commit generalized it to ANY tool ("any sufficiently fast tool can settle before the UI dispatch creates its card") and extracted the helper.
**Invariant:** Exactly-once side effects: replay-through-`#endHandler` is forbidden — `#settleHeldCompletion` updates only the component; two tests pin warning-fires-once and setTodos-called-once. Hold condition is `!#toolTimelineComponents.has(id)` — NOT "no pendingTools entry" — because cumulative stream updates must not recreate/settle twice. Re-key consumes under the NEW id (server-resolved completions land under `newId` while the card was keyed by old).
**Probe:** `test/event-controller-cursor-todo.test.ts` — `"settles a fast eval completion that outruns its streamed block"` pins blocks=1 + pendingTools=0 + `isTranscriptBlockFinalized()===true`; `"fires the failure warning exactly once…"` pins the once-only side-effect rule.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "orphanedToolCompletions settleHeldCompletionIfPresent", limit: 10, fields: ["signature", "name", "file"] });
```
Live-resolved @2b66ee69: `#settleHeldCompletionIfPresent event-controller.ts:1482-1487`.

## Verdict
Adopt hold-and-settle-on-create for any event stream where completion can outrun creation (async UI dispatch vs sync callbacks); keep side-effects-at-first-arrival strictly separated from component mutation. Adapt the trigger points to your component lifecycle; preserve the has-component gate shape (a weaker pendingTools check double-settles). Runner caveat as recorded.
