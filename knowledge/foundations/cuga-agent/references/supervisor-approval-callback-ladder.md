<!-- capsule-v2 -->
# Supervisor callback routing — approval-resume ladder with the final_answer guard ordering trap

**Source:** cuga-agent Apache-2.0 `main@5de53ade`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** After a subgraph completes (or a HITL approval interrupt resolves), one callback node must resume, deny, or finalize. How do you order the branches so an approval message — which IS a `final_answer` set by the interrupt — doesn't get mistaken for task completion and short-circuit the resume?

## The callback contract
**Path/Symbol:** `src/cuga/backend/cuga_graph/nodes/cuga_supervisor/cuga_supervisor_node.py` (`CugaSupervisorNode.callback_node` :203-359).
**Signature:** `async callback_node(state: AgentState, config) -> Command`; branch keys are `state.sender`, `state.hitl_response.action_id ∈ {AGENT_APPROVAL, TOOL_APPROVAL}`, `state.hitl_action.action_id`, then answer presence.
**Data Shape:** `hitl_action`/`hitl_response` carry `action_id` + `confirmed`; policy decisions append to `supervisor_metadata.policy_decisions` via `append_policy_decisions(decision_from_metadata(metadata, outcome=APPROVED|DENIED))`.

### Decisive source
```python
# :221-225 — the ordering trap, in the author's own words
# Tool-approval HITL resume (Slice B). Kept separate from the
# AGENT_APPROVAL block below because the approval interrupt sets
# final_answer, which that block's `not final_answer` guard would
# skip. Additive: only fires for TOOL_APPROVAL, which never occurs
# for Supervisor unless settings.policy.enabled.

# :226-230 — TOOL_APPROVAL resume keyed on sender + action id, BEFORE the guard
if (state.sender == "WaitForResponse"
    and state.hitl_response
    and state.hitl_response.action_id == ActionIds.TOOL_APPROVAL):

# :258-261 — approve ⇒ clear BOTH hitl fields AND the approval text itself
sd["final_answer"] = ""  # clear approval message so the subgraph runs
return Command(update=..., goto="CugaSupervisorSubgraph")

# :323-334 — first-pass approvals route to HITL with sender set for the return trip
if state.hitl_action and state.hitl_action.action_id in (ActionIds.AGENT_APPROVAL,
                                                          ActionIds.TOOL_APPROVAL):
    state.sender = self.name          # WaitForResponse returns here via sender
    return Command(update=state.model_dump(), goto=NodeNames.SUGGEST_HUMAN_ACTIONS)
```

**Flow:** (1) TOOL_APPROVAL resume from WaitForResponse: append APPROVED/DENIED decision to metadata; approve ⇒ re-enter subgraph with `approval_required=False/user_approved=True`, hitl fields nulled, `final_answer=""`; deny ⇒ canned "Execution Cancelled … {policy_name}" answer, `execution_complete=True`, FinalAnswerAgent. (2) AGENT_APPROVAL resume (only when `not final_answer`): confirm ⇒ re-enter subgraph keeping `hitl_response` set (execute node consumes it); deny ⇒ "Agent execution was cancelled by user." (3) Fresh `hitl_action` for either approval type ⇒ route to SuggestHumanActions with `sender=self.name`. (4) `final_answer` present ⇒ FinalAnswerAgent. (5) Fallback: last supervisor message content becomes the answer; last resort is a canned "no answer was generated" string.
**Invariant:** branch ORDER is load-bearing — the generic HITL handler's `not state.final_answer` guard would swallow tool-approval resumes because approval interrupts legitimately set `final_answer` as their user-facing message; hence TOOL_APPROVAL gets its own earlier block keyed on `sender=="WaitForResponse"` + action id. Resume paths must clear the interrupt's artifacts (`hitl_action`, `hitl_response`, approval text) or the subgraph re-triggers the UI loop. Denials always terminate with an explicit `execution_complete=True` + human-readable cancellation answer; nothing ever raises out of the callback.

**Probe:** no dedicated unit test pins this callback — COVERAGE CAVEAT (recorded honestly). Deterministic probes: source needles above verified verbatim; graph retrieval resolves `callback_node` at :203-359; the sibling CugaLite callback (`cuga_lite_node.py:374-459`) shows the same ladder shape.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "callback_node TOOL_APPROVAL AGENT_APPROVAL WaitForResponse SuggestHumanActions", limit: 10 });
```

## Verdict
Adopt the resume-ladder shape (resume-specific branches BEFORE generic guards, sender-keyed return addressing, artifact-clearing on resume, denial = explicit termination answer). Adapt action-id enum and metadata schema to your host. Omit nothing else — the ordering trap comment is the capsule.
