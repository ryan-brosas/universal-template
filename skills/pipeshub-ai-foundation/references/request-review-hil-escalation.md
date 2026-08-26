<!-- capsule-v2 -->
# request_review (HIL escalation with proceed-when-unconfigured fallback)

## Source
pipeshub-ai Apache-2.0 `main@4a02110d`; Codebase Memory `pipeshub-ai`. **Question:** How does an agent explicitly escalate a medium-confidence decision to human/senior review mid-loop — and what happens when no reviewer is configured?

## Path/Symbol
`tools/builtin/planning/request_review.py` — `RequestReviewTool.handle()` (:63–103). Companions: `hooks/middleware/builtin/supervisor_gate.py` (deterministic LOW half), `modules/stores/hil/base.py` (`HILRequest`, `HILRequestType.PLAN_REVIEW`).

## Signature
`handle()` builds `HILRequest(request_type=PLAN_REVIEW, run_id=agent.run_ctx.run_id, session_id=agent.session_id, question=question, context={"goal": ctx.goal.description})`, then `request_id = await runtime.hil_store.submit(hil_request)` (:82–89).

## Data Shape
Arg: `question` (required, phrased as a yes/no). Result content always `{"approved": bool, "reason": str}` — approved=True/reason="no HIL store configured — proceeding" when unconfigured (:76–80); after wait: `{"approved": hil_response.approved, "reason": hil_response.answer or ""}`.

### Decisive source
```python
request_id = await runtime.hil_store.submit(hil_request)

await obs.save_checkpoint(
    agent, "hil_pause", ctx.goal, ctx.messages, ctx.turn_index,
    current_tool="request_review",
    hil_request_id=request_id,
    pending_tool_call_id=call.id,
)

hil_response = await runtime.hil_store.wait_for_response(request_id)
```

**Flow:** submit → CHECKPOINT BEFORE BLOCKING (kind `hil_pause`, carrying BOTH ids) → `wait_for_response` blocks until the human answers → approval dict returned as normal tool result. This is the same dual-id bridge as hil-pause-resume-identity: `hil_request_id` routes the answer back across restarts; ORIGINAL `call.id` addresses the provider ToolMessage so resume can complete this exact call.

**Invariant:** Escalation is inherently interactive ⇒ it can NEVER be a hook (a hook can only enforce a rule, never decide to ask a human) — that's why it's a tool any agent may call mid-loop, not just the root preamble that calls `Supervisor.review()` today. No-hil-store ⇒ PROCEED (approved=True), mirroring Supervisor.review()'s own fallback — missing infrastructure must not wedge the run.

**Probe:** No dedicated tool unit test (coverage caveat): the checkpoint/dual-id contract it depends on is pinned by tests for checkpoint-snapshot-contract + hil-pause-resume-identity; HIL store protocol exercised in tests/unit/agent_loop_lib/agent/*hil* paths.

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph --project pipeshub-ai --semantic-query '["RequestReviewTool","HILRequest","wait_for_response"]'
```

## Verdict
Adopt submit→checkpoint-before-blocking→wait ordering and the proceed-on-unconfigured fallback; adapt HIL store interface. The interactive-escalation-as-tool (never-hook) principle is the portable core.
