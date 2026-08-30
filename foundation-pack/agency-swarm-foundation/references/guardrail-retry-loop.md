<!-- capsule-v2 -->
# Guardrail retry loop — how do output-guardrail failures become corrective feedback instead of dead runs?

**Source:** agency-swarm MIT `main@4d1c35a6dd5ef038a5d15b39803459ff0b5f5578`; Codebase Memory `ext-agency-swarm`. **Question:** How does the run loop convert a tripped output guardrail into a retry with guidance appended, and what distinguishes the input-guardrail path?

## run_with_guardrails retry loop over perform_single_run
**Path/Symbol:** `src/agency_swarm/agent/execution_helpers.py:perform_single_run` (:56-89) + `run_with_guardrails` (:95-190); feedback writer `execution_guardrails.append_guardrail_feedback`.
**Signature:** `run_with_guardrails(*, agent, history_for_runner, master_context_for_run, sender_name, agency_context, hooks_override, run_config_override, kwargs, current_agent_run_id, parent_run_id, run_trace_id, validation_attempts: int, raise_input_guardrail_error: bool) -> tuple[RunResult, MasterContext]`.
**Data Shape:** `validation_attempts` counts RETRIES (1 = one retry after first failure; 0 = raise immediately). The loop MUTATES `history_for_runner` in place between attempts by appending the guardrail feedback items.

### Decisive source
```python
attempts_remaining = int(validation_attempts or 0)
while True:
    try:
        return await perform_single_run(...), master_context_for_run
    except OutputGuardrailTripwireTriggered as e:
        history_for_runner = append_guardrail_feedback(..., include_assistant=True)
        if attempts_remaining <= 0:
            raise e                                   # retries exhausted → surface
        attempts_remaining -= 1
        continue                                      # SAME context object, grown history
    except InputGuardrailTripwireTriggered as e:
        history_for_runner = append_guardrail_feedback(..., include_assistant=False)
        if not raise_input_guardrail_error:
            _, guidance_text = extract_guardrail_texts(e)
            return RunResult(input=history_for_runner, new_items=[], raw_responses=[],
                             final_output=guidance_text, ...), master_context_for_run
        raise e
    except Exception as e:
        raise AgentsException(f"Runner execution failed for agent {agent.name} (cause: {type(e).__name__})") from e
```

**Flow:** `perform_single_run` is deliberately the bare primitive (MCP AsyncExitStack connect + `agency_system_reminder_run` + `Runner.run`, default `max_turns=1000000`) so retry orchestration never re-enters MCP setup — the exit stack closes per attempt and reconnects on the next. Output tripwires append assistant+feedback and re-run; input tripwires either return the guidance TEXT as a normal final output (fail-open, default) or raise.
**Invariant:** (1) Retry reuses the SAME MasterContext — only history grows, so tool state and usage accumulation stay continuous; (2) the exhausted-retry raise happens AFTER feedback is appended, so persisted history shows the failed exchange plus guidance (post-run save covers it); (3) every other exception is wrapped in `AgentsException` naming the agent and cause TYPE (not message) to keep error classes stable for callers; (4) attachments cleanup runs in `finally` per attempt — temp files never survive across retries.
**Probe:** `tests/test_agent_modules/test_guardrail_validation.py` pins the append+retry contract (see also `tests/integration/guardrails/` end-to-end suites at HEAD).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-agency-swarm", query: "run_with_guardrails OutputGuardrailTripwireTriggered append_guardrail_feedback", limit: 10 });
```

## Verdict
Adopt the retry-with-grown-history loop and fail-open input-guardrail default; adapt the feedback item shape to your provider's message format; omit the AgentsException wrapper only if your caller already has a stable error taxonomy. Direct tests pin both guardrail paths at HEAD.
