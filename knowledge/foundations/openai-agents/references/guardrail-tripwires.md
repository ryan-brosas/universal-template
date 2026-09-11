<!-- capsule-v2 -->
# Guardrail tripwires — how safety checks halt a run without adding latency

**Source:** OpenAI Agents Python MIT `main@cb8a2e7e7dd83a427cff9076e58356d00c4f90b2`; Codebase Memory `openai-agents-python`. **Question:** How do input/output guardrails stop a run, and why are they parallel-by-default?

## Parallel guardrail tripwires
**Path/Symbol:** `src/agents/guardrail.py:InputGuardrail` / `OutputGuardrail` / `input_guardrail` / `output_guardrail` (1-343).
**Signature:** `InputGuardrail(guardrail_function, name=None, run_in_parallel=True)`; `OutputGuardrail(guardrail_function, name=None)`; decorators `input_guardrail(...)` / `output_guardrail(...)`.
**Data Shape:** Every guardrail function returns `GuardrailFunctionOutput{output_info: Any, tripwire_triggered: bool}`. Input guardrail fn takes `(RunContextWrapper[TContext], Agent, str | list[TResponseInputItem])`; output guardrail fn takes `(RunContextWrapper, Agent, agent_output: Any)`.

### Decisive source
```python
@dataclass
class GuardrailFunctionOutput:
    output_info: Any
    tripwire_triggered: bool  # if True, agent execution halts

# InputGuardrail.run_in_parallel: bool = True  # (:100-104)
# "Whether the guardrail runs concurrently with the agent (True, default) or before the agent starts (False)."
```

**Flow:** A triggered tripwire raises `InputGuardrailTripwireTriggered` / `OutputGuardrailTripwireTriggered` — an **exception, not a return value**, so no downstream code can accidentally ignore it. Input guardrails with `run_in_parallel=True` run concurrently with the agent (a fast classifier cancels a slow generation without adding latency on the happy path); `run_in_parallel=False` gates BEFORE the model is called at all. Output guardrails run against the final output; results carry `output_info` for tracing/explanations. Both `run()` methods accept sync or awaitable functions (`inspect.isawaitable` dispatch) and raise `UserError` if the fn isn't callable.
**Invariant:** A safety check must not be ignorable — halting is an exception, never a bool a caller might forget to check.
**Probe:** `tests/test_guardrails.py` (input/output tripwire raise + parallel timing); `tests/test_stream_input_guardrail_timing.py` (parallel-vs-gated latency); `tests/test_output_guardrail_cancellation.py`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openai-agents-python", query: "InputGuardrailTripwireTriggered guardrail", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the tripwire-as-exception contract and parallel-by-default input guardrails; adapt the exact decorator overloads; omit provider-specific tracing of `output_info`. Direct tests exist and pin the raise-on-tripwire behavior.
