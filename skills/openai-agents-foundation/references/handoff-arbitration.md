<!-- capsule-v2 -->
# Handoff arbitration — one winner, honest losers, faithful history

**Source:** OpenAI Agents Python MIT `main@cb8a2e7e7dd83a427cff9076e58356d00c4f90b2`; Codebase Memory `openai-agents-python`. **Question:** When a model emits multiple handoff calls, how is a single winner chosen without corrupting history or leaving unmatched call_ids?

## Handoff arbitration
**Path/Symbol:** `src/agents/run_internal/turn_resolution.py` (handoff dispatch, :563-573, :702-710, :1985-1990).
**Signature:** internal handoff dispatch within `execute_tools_and_side_effects`; `SingleStepResult` carries `new_step_items` + optional `input_items`.
**Data Shape:** `SingleStepResult` carries BOTH `new_step_items` (full, for persistence) and optional `input_items` (filtered, for the model).

### Decisive source
```python
# If the model emits multiple handoff calls in one response, only the FIRST executes.
# Every loser receives a synthetic tool output reading exactly:
#   "Multiple handoffs detected, ignoring this one."  (:563-573)
# Why fabricate outputs? Because providers reject unmatched call_ids — the losers must
# be answered even though they lost.
```

**Flow:** The winning handoff runs inside a `handoff_span`, fires hooks concurrently (`gather_with_cancel`), and produces next-turn input through an optional filter chain. Two invariants: (1) server-managed conversations refuse client-side history surgery — a configured `input_filter` raises `UserError` verbatim ("Remove Handoff.input_filter or RunConfig.handoff_input_filter, or disable conversation_id, previous_response_id, and auto_previous_response_id", :509-513); nesting silently downgrades with a warning. (2) Session history vs model input split (:702-710): an input filter can slim what the next agent sees without corrupting durable history. On RESUME, already-executed handoffs are filtered by call_id collected from existing `HandoffOutputItem`s (:1985-1990), so replay never double-fires.
**Invariant:** Handoffs need three guarantees — single-winner arbitration with fake outputs for losers, validated filters, and a session/model split so filtering never corrupts history.
**Probe:** assert the second `ToolCallOutputItem.output` equals the multiple-handoffs message; assert `UserError` on input filters under server-managed conversations.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openai-agents-python", query: "Multiple handoffs detected ignoring this one", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt single-winner arbitration with fabricated outputs for losers, validated filters, and the session/model split; adapt the exact message text; omit server-managed-conversation refusal specifics.
