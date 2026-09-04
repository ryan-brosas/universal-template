<!-- capsule-v2 -->
# Schedule delivery routing ladder — how does a finished scheduled run find its way back to the right chat thread, and who is allowed to deliver it?

**Source:** Cline Apache-2.0 `main@4f836ae7d0ed29ece7ef4a2a478deb470fdd056e`; Codebase Memory `cline`. **Question:** When a hub schedule execution completes or fails, how does the connector decide (a) whether THIS instance should deliver the result and (b) which thread gets it?

## Three-key delivery routing with an instance-ownership gate
**Path/Symbol:** `apps/cli/src/connectors/adapters/slack.ts:deliverScheduledResult` (:400-489, wired at :1229-1288 via `client.streamEvents`); cross-adapter twin `apps/cli/src/connectors/adapters/telegram.ts:deliverScheduledResult` (:319-459); routing primitive `apps/cli/src/connectors/thread-bindings.ts:findBindingForDeliveryTarget` (:503-531).
**Signature:** `deliverScheduledResult(input: { bot; slack; client; logger; bindingsPath; userName; scheduleId; executionId; sessionId?; status; errorMessage?; hookCommand? }): Promise<void>`; `findBindingForDeliveryTarget<TState>(bindings, input: { bindingKey?; threadId?; participantKey? }): { binding; key } | undefined`.
**Data Shape:** Delivery coordinates persist in `schedule.metadata.delivery = { adapter, userName?, threadId?, bindingKey?, participantKey? }` — written at schedule-creation time so delivery survives connector restarts (bindings re-read from disk, never held in memory). Hub events `schedule.execution.completed|failed` carry `{scheduleId, executionId, sessionId?, status, errorMessage?}`.

### Decisive source
```ts
const delivery = schedule?.metadata?.delivery as Record<string, unknown> | undefined;
if (!delivery || delivery.adapter !== "slack") {
	return;
}
const targetUser = typeof delivery.userName === "string" ? delivery.userName.trim() : "";
if (targetUser && targetUser !== input.userName) {
	return; // another connector instance owns this delivery
}
...
const match = findBindingForDeliveryTarget(bindings, { bindingKey, threadId, participantKey });
const deliveryThreadId = match?.key || threadId || bindingKey;
if (!binding?.serializedThread) {
	return;
}
```

**Flow:** hub event (fire-and-forget `void`, alongside a `rpc.server.shutting_down` listener that requests stop) → fetch schedule → ownership gate: `delivery.adapter` must match AND a non-empty `delivery.userName` must equal THIS connector's userName (multi-instance rule from the state-file plane, applied to schedules) → presence gate: at least ONE of threadId/bindingKey/participantKey → binding resolution ladder: bindingKey exact → participant scan → threadId exact → participantKey scan (`findBindingForDeliveryTarget`, control bindings excluded at both exact slots) → no serializedThread ⇒ silent return → success with sessionId posts the session's reply text (empty text ⇒ explicit "completed, but no assistant reply text was found" body — never a silent success); failure posts `{status}` + errorMessage → post wrapped in `withSlackBindingBotToken` with invalid_thread_ts reaping (error re-thrown after cleanup).
**Invariant:** (1) Delivery identity is resolved from PERSISTED schedule metadata + persisted bindings, never from in-memory state, so a restart between schedule creation and execution cannot orphan the result. (2) Exactly one connector instance delivers: the userName gate returns silently (not an error) when another instance owns the schedule. (3) A successful execution with no reply text still produces a visible message. The telegram twin confirms the ladder is adapter-independent: same three-key routing, telegram-format fallback instead of token wrapping.
**Probe:** `apps/cli/src/connectors/adapters/slack.test.ts` (indirect: binding-lookup and invalid_thread_ts cases); `apps/cli/src/connectors/task-updates.test.ts` "finds a binding by session id in either binding slot" (the session-routed sibling). Direct probe: `grep -n "delivery.adapter !==" apps/cli/src/connectors/adapters/slack.ts` → exactly 1 hit at :412.

## Get live surrounding code
**Retrieve:** *(canonical call for a connected session — NOT executed this pass)*
```ts
await mcp.codebase_memory.get_code_snippet({ project: "cline", file: "apps/cli/src/connectors/adapters/slack.ts", symbol: "deliverScheduledResult" });
```

## Verdict
Adopt the ladder: persisted delivery metadata → instance-ownership gate → three-key binding resolution → explicit no-reply-text body → token-scoped post with self-heal. Adapt the metadata field names and the platform post wrapper. Omit the hub event plumbing (transport-specific). Coverage caveat: no dedicated deliverScheduledResult suite exists; behavior is pinned by source read at the pin plus the sibling binding-lookup tests and the cross-adapter telegram twin.
