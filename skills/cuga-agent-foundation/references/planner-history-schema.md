<!-- capsule-v2 -->
# Planner history schema — how does one discriminated record serve every router action without a validator?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** What shape carries each planner action's inputs and outputs across loop iterations, and which fields are load-bearing vs deliberately loose?

## Loose-typed HistoricalAction, typed output payloads
**Path/Symbol:** `src/cuga/backend/cuga_graph/state/api_planner_history.py:HistoricalAction` (:83-92), `CoderAgentHistoricalOutput` (:36-40), `ApiFilteringAgentHistoricalOutput` (:53-56), `ConcludeTaskHistoricalOutput` (:63-66).
**Signature:** `HistoricalAction(action_taken: Literal['CoderAgent','ConcludeTask','ApiShortlistingAgent','ConsultWithHuman'], input_to_agent: Optional[Any], agent_output: Optional[Any])`.
**Data Shape:** writers store pydantic models in `agent_output`; readers (`str(state.api_planner_history)` into reflection prompts) see their reprs. A `Field(discriminator='agent_type')` Annotated union exists but is UNUSED by `HistoricalAction`.

### Decisive source
```python
class HistoricalAction(BaseModel):
    """
    Represents a single action entry in the history of actions.
    """
    action_taken: Literal['CoderAgent', 'ConcludeTask', 'ApiShortlistingAgent', 'ConsultWithHuman'] = Field(
        ..., description="The type of action that was performed."
    )
    input_to_agent: Optional[Any] = None
    agent_output: Optional[Any] = None
```
with ~75 lines of validator commented out below it (:94-170) — the deliberate looseness decision.

**Flow:** `collect_history` appends `{action, input}` BEFORE the sub-node runs; each terminal writer mutates the SAME entry in place: ApiCoder sets `agent_output = CoderAgentHistoricalOutput(variables_summary≤5000 chars, final_output)`; the missing-api escape overwrites `final_output` with guidance text; ConcludeTask relies on `input.final_response`. Reflection then interpolates `str(history)` into the strategic prompt.
**Invariant:** In-place mutation of `history[-1]` (never append-on-completion) is what pairs input with output; appending would desynchronize reflection. `Any` typing survives AgentState checkpoint round-trips precisely because there's no strict validation — tightening it breaks replayed checkpoints written by older versions.
**Probe:** Recorded upstream gap — no dedicated unit test. Deterministic: `grep -n "agent_output" src/cuga/backend/cuga_graph/nodes/api/api_code_planner.py | head -2` shows the in-place write (:48).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "HistoricalAction collect_history api_planner_history agent_output", limit: 6, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt append-input-first/mutate-output-in-place history pairing and Literal-tagged but loosely-typed records where checkpoints must stay forward-compatible. Adapt the action vocabulary to your router. Omit the dead discriminator union (upstream kept it aspirational).
