<!-- capsule-v2 -->
# LLM event publisher — how do you persist one provider turn as durable session events with protocol-violation detection and safe settlement?

**Source:** opencode MIT `dev@03521003fafd`; Codebase Memory `opencode`. **Question:** The v2 runner streams LLMEvents (text/reasoning/tool fragments) from a provider and must turn them into durable SessionEvents that projectors converge into tables — without executing tools, without starting continuation turns, and without letting a misbehaving provider stream (duplicate IDs, name changes, results before calls) corrupt the log. What is the per-turn state machine?

## Fragment accumulation with die-on-violation
**Path/Symbol:** `packages/core/src/session/runner/publish-llm-event.ts` (`createLLMEventPublisher` :54-423, `fragments` :91-117, `startAssistant` :66-76, `publish` :246-408).
**Signature:** `createLLMEventPublisher(events, {sessionID, agent, model, snapshot?}) → {publish(event, outputPaths?), flush, failAssistant(message), failUnsettledTools(message, hostedOnly?), hasActiveAssistant, hasAssistantStarted, hasProviderError, stepSettlement(), startAssistant, assistantMessageID(callID)}`.
**Data Shape:** tools = `Map<callID, {assistantMessageID, name, inputEnded, called, settled, providerExecuted, providerMetadata?}>`; fragment chunks = `Map<id, string[]>`; stepSettlement = `{finish: string, tokens: {input, output, reasoning, cache:{read, write}}}`.

### Decisive source
```ts
// publish-llm-event.ts:91-117 — the fragment factory: start/append/end/flush, every violation dies
const start = (id) => Effect.suspend(() => {
  if (chunks.has(id)) return Effect.die(`Duplicate ${name} start: ${id}`)
  chunks.set(id, []); return Effect.void
})
const append = (id, value) => Effect.suspend(() => {
  const current = chunks.get(id)
  if (!current) return Effect.die(`${name} delta before start: ${id}`)
  current.push(value); return Effect.void
})
const end = Effect.fnUntraced(function* (id, providerMetadata?) {
  const current = chunks.get(id)
  if (!current) return yield* Effect.die(`${name} end before start: ${id}`)
  yield* ended(id, current.join(""), providerMetadata); chunks.delete(id)
})
```

**Flow:** the assistant message ID is created lazily on the first startAssistant and publishes Step.Started carrying the pre-turn snapshot; every text/reasoning/tool-input fragment accumulates deltas in memory and publishes its *Ended* event only when the fragment closes (deltas publish live as *Delta* events). Protocol violations are DEFECTS (Effect.die), not typed errors: duplicate start, delta-before-start, end-before-start, tool name change between events for one callID, duplicate tool call, result-before-call, duplicate non-error result (an error result after settle is silently dropped), duplicate step finish. A die here means "the provider stream broke a wire contract" — the runner's interrupt/failure paths settle everything and the turn fails loudly rather than projecting garbage.

**Invariant:** each fragment ID starts once, appends only after start, ends once; each tool callID has one stable name across all its events; at most one Tool.Called and one settling result per callID; at most one step finish per turn.
**Probe:** `packages/core/test/session-runner-tool-events.test.ts` (read whole, 136L): "local tool success serializes media base64 once and reconstructs from structured content" pins JSON.stringify(success).split(base64).length===2 AND no `result` property on local success; "provider-executed success retains its compatibility result" pins `result` present when providerExecuted; "binary failure emits no success event" pins failed-only; "old success event data containing result still decodes" pins backward schema compatibility; "step finish records settlement without publishing step ended" pins no `session.next.step.ended.2` + stepSettlement {finish:"stop"}. Source pin:
```bash
grep -n 'Duplicate step finish' packages/core/src/session/runner/publish-llm-event.ts  # expect 1 (:399)
grep -n 'const fragments' packages/core/src/session/runner/publish-llm-event.ts        # expect 1 (:91)
```

## Tool settlement + failure ladders
**Path/Symbol:** same file (`settledOutput` :46-52, `tool-call` case :300-322, `tool-result` case :323-358, `failAssistant` :199-209, `failUnsettledTools` :213-228, `step-finish` case :396-402, `tokens` :20-28).
**Signature:** `settledOutput(output?: ToolOutput, result: ToolResultValue) → {structured, content} | {error}`; runner call sites in `runner/llm.ts` (:252/:299-300/:306/:314-316/:321).
**Data Shape:** Tool.Success carries structured+content+outputPaths (+raw result ONLY when provider.executed); Tool.Failed carries error (+result for provider-reported errors) + provider{executed, metadata?}.

### Decisive source
```ts
// publish-llm-event.ts:300-322 — tool-call self-heals missing input events, then settles once
case "tool-call": {
  if (!tools.has(event.id)) yield* startToolInput(event)
  const tool = tools.get(event.id)!
  if (!tool.inputEnded) yield* endToolInput(event)
  if (tool.name !== event.name) return yield* Effect.die(`Tool call name changed for ${event.id}: ...`)
  if (tool.called) return yield* Effect.die(`Duplicate tool call: ${event.id}`)
  tool.called = true; tool.providerExecuted = event.providerExecuted === true
  ...yield* events.publish(SessionEvent.Tool.Called, {...})
}
// publish-llm-event.ts:213-228 — failUnsettledTools: hostedOnly skips locally-executed tools
for (const [callID, tool] of tools) {
  if (tool.settled || (hostedOnly && !tool.providerExecuted)) continue
  tool.settled = true
  yield* events.publish(SessionEvent.Tool.Failed, {..., error: { type: "unknown", message },
    provider: { executed: tool.providerExecuted, ...(metadata...) } })
}
```

**Flow:** tool-call auto-starts/auto-ends input fragments for providers that skip them, records providerExecuted+metadata, and publishes Tool.Called. tool-result converts through settledOutput: an error result → Tool.Failed carrying the raw result; a content result uses the explicit ToolOutput when given else ToolOutput.fromResultValue (throwing on unsupported shapes), and Tool.Success includes the raw result ONLY when provider.executed — a local success omits it so media base64 is serialized exactly once across the durable event. step-finish flushes open fragments, clears assistantActive, and records stepSettlement WITHOUT publishing Step.Ended — the runner reads settlement via stepSettlement() and decides continuation itself. tokens() normalizes usage with safe() clamping non-finite/negative to 0 (input=nonCachedInputTokens, output=visibleOutputTokens). The runner's failure ladders: max-steps → failUnsettledTools("Tools are disabled after the maximum agent steps"); provider stream ends with open hosted tools → failUnsettledTools("Provider did not return a tool result", true) THEN failAssistant(reason); interrupt → failUnsettledTools("Tool execution interrupted") + failAssistant("Provider turn interrupted") when an assistant was active; provider-error → providerFailed latch + failAssistant.

**Invariant:** every started tool ends in exactly one of Called→(Success|Failed); failAssistant is idempotent (latch) and always flushes first; hostedOnly failures never touch locally-executed tools; a turn's usage is recorded at most once, at step finish; no Step.Ended is ever published by the publisher (settlement is runner-owned).
**Probe:** session-runner-tool-events.test.ts (above) pins the serialization split and settlement-without-end; session-runner.test.ts "projects reasoning and tool events without executing or continuing tools" (:1372+) pins the full event sequence including toolError→Failed, provider-executed web_search success with metadata, and step-finish usage normalization. Source pin:
```bash
grep -n 'provider.executed ? { result: event.result } : {}' packages/core/src/session/runner/publish-llm-event.ts  # expect 1
grep -c 'failUnsettledTools(' packages/core/src/session/runner/llm.ts  # expect 7 (:252/:299/:306/:314/:321 + overflow-recovery :346/:348)
```

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "opencode", query: "createLLMEventPublisher fragments failUnsettledTools settledOutput stepSettlement Tool.Success Tool.Failed Step.Started", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the closure-per-turn publisher as the seam between a streaming provider and durable events: accumulate fragments in memory, publish Ended on close, and treat every wire-contract violation as a defect (die) so corrupted streams fail the turn instead of poisoning projectors. Adopt the self-healing tool-call (auto-start/auto-end input) — real providers skip input events, and the durable log must still be complete. Adopt the media-once rule: raw results ride along only for provider-executed tools; local successes carry structured+content so binary payloads serialize once. Adopt runner-owned settlement (stepSettlement read, no Step.Ended published) so continuation policy stays out of the persistence layer. Adapt the token normalization to your provider's usage fields; omit hostedOnly if you have no provider-side tool execution. Direct tests read whole (session-runner-tool-events.test.ts 136L) + section (session-runner.test.ts :1372+); bun runner blocked at this checkout (no node_modules), probes are byte-exact greps.
