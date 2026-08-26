<!-- capsule-v2 -->
# Priority pending-message drain with end-of-run redirect — how do queued steering messages get delivered so they are never silently lost at termination?

## Source / Question
`pydantic_ai_slim/pydantic_ai/capabilities/_pending_messages.py` @ `main@b3cdbc96` (MIT); Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** A run holds an out-of-band queue of messages enqueued by tools mid-run ('asap' = steering, 'when_idle' = follow-up). Where exactly do you drain each priority so nothing is lost when the agent would otherwise return `End`, and what must the redirect request look like? A porter will drain only at request-build time and drop everything that arrives during the final step.

## Path / Symbol
`capabilities/_pending_messages.py` — `_drain_by_priority(queue, priority)` (:22–35, mutates `queue[:]` in place), `_stamped_messages(pending, *, fallback_run_id, fallback_conversation_id)` (:38–56, fill-only-unset stamping via `fill_run_metadata`), `PendingMessageDrainCapability` (:59–178): `get_ordering() → CapabilityOrdering(position='outermost')` (:77–78), `before_model_request` (:84–111), `after_node_run` redirect (:113–178), non-ModelRequest tail guard (:165–170).

## Signature
```python
def _drain_by_priority(queue: list[PendingMessage], priority: PendingMessagePriority) -> list[PendingMessage]
async def after_node_run(self, ctx, *, node, result: AgentNode | End[FinalResult]) -> AgentNode | End[FinalResult]
```

## Data Shape
Queue lives on `ctx.pending_messages` (always present during a run — asserted, not checked). Each `PendingMessage` carries enqueue_id + pre-built `ModelMessage`s whose `timestamp/run_id/conversation_id` may be unset. Drain emits one `EnqueuedMessagesEvent(enqueue_id, messages=tuple(...))` PER enqueue call, in enqueue order, describing messages exactly as delivered.

### Decisive source
The terminate-time drain order and split (:140–149):
```python
# Pi-mono parity: drain `'asap'` first so anything that arrived during the
# final step (e.g. a background task completing while the model produced
# its final response) gets delivered before `'when_idle'` messages ...
leftover_asap = _drain_by_priority(ctx.pending_messages, 'asap')
when_idle = _drain_by_priority(ctx.pending_messages, 'when_idle')
if not leftover_asap and not when_idle:
    return result
drained = [*leftover_asap, *when_idle]
```

**Flow:** `'asap'`: drained into EVERY upcoming model request via `before_model_request` — appended to BOTH `request_context.messages` (model sees this step) and `ctx.messages` (persists in history); framework stamps only UNSET metadata because producers may have supplied their own and downstream capabilities might append more. Terminate time (`after_node_run` sees `End`): drain leftover 'asap' first, then 'when_idle'; each priority appended independently so history keeps the priority split visible (matches pi-mono's separate steering/follow-up turns) — `_clean_message_history` re-merges adjacent requests with compatible instructions on the wire so the model still sees one turn. LAST drained message becomes the redirect `ModelRequestNode(request=final)`; all earlier ones go to history before the redirect. If the final message is not a `ModelRequest` → `UserError` naming the actual type (checked, not asserted, because producers can construct PendingMessage directly).

**Invariant:** A `'when_idle'` message arriving at the moment of termination PREVENTS the end — the agent gets another turn rather than terminating with the message lost. Outermost position ensures 'asap' drains before user capabilities see the request and the redirect happens after all other `after_node_run` hooks (which run reversed). Re-stamping the final request later is harmless (lifecycle stamp overwrites).

**Probe:** `tests/test_capabilities.py` — `test_enqueue_when_idle_message_prevents_end` (:17057, call_count==3 proves the extra turn), `test_enqueue_when_idle_redirects_after_output_tool_end` (:17147), `test_enqueue_asap_message_from_tool` (:16646), `test_multiple_enqueue_delivery_events_keep_order` (:16793), `test_pending_message_drain_capability_is_not_spec_constructible` (:17607).

## Get live surrounding code
**Retrieve:**
```
search_graph --project mnt-hdd-utopia-inspo-pydantic-ai --query 'PendingMessageDrainCapability after_node_run ModelRequestNode redirect'
```

## Verdict
**Adopt** the two-priority two-site drain (request-build + terminate-time redirect), the drain-'asap'-first ordering at termination, the append-to-history-and-request duality, and the fill-only-unset stamping. **Adapt** the UserError wording; keep the check-don't-assert posture for producer-controlled queues. **Omit** the EnqueuedMessagesEvent plumbing only if your host has no event stream — but then you still need the drain sites.
