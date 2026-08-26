<!-- capsule-v2 -->
# Tool-choice resolver — user-facing choice to canonical provider form with output-tool folding

## Source / Question
`pydantic_ai_slim/pydantic_ai/models/_tool_choice.py` @ `main@b3cdbc96` (MIT); Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** The user's `tool_choice` setting controls FUNCTION tools only, but providers must also be told about framework-internal OUTPUT tools — how does one resolver fold both into a canonical five-value form without letting users force-call an output tool? A porter will pass tool_choice through raw and break structured-output runs.

## Path / Symbol
`models/_tool_choice.py` — `resolve_tool_choice()` whole file (:13–181), `ResolvedToolChoice = Literal['none','auto','required'] | tuple[Literal['auto','required'], set[str]]` (:8).

## Signature
```python
def resolve_tool_choice(
    model_settings: ModelSettings | None,
    model_request_parameters: ModelRequestParameters,
) -> ResolvedToolChoice: ...
```

## Data Shape
Input vocabulary: `None`, `'auto'`, `'none'`, `'required'`, `[]`, `list[str]` (restrict+require named function tools), `ToolOrOutput` (combine named function tools with all output tools). Output canonical form: `'none' | 'auto' | 'required' | ('auto', names) | ('required', names)` where `names` sets are the ONLY tools available in that mode.

### Decisive source — the documented contract (:16–47)
```python
"""Input behavior:
    - `None` / `'auto'`: Returns `'auto'` if direct output allowed, else `'required'`.
    - `'none'` / `[]`: Disables function tools. If output tools exist, returns them with
        appropriate mode. Otherwise returns `'none'`.
    - `'required'`: Requires function tool use. Raises if no function tools are defined.
    - `list[str]`: Restricts to specified tools with `'required'` mode. Validates tool names.
    - `ToolOrOutput`: Combines specified function tools with all output tools.
        Returns `'auto'` mode if direct output is allowed, otherwise `'required'`.
Raises:
    UserError: If tool_choice is incompatible with the available tools or output configuration."""
```

**Flow:** read `model_settings.get('tool_choice')` → validate against the run's actual function/output tool inventory (unknown names and required-with-no-function-tools raise UserError BEFORE any network call) → when direct text/image output is impossible (output tools present and forced) 'auto' degrades to 'required' so the model cannot answer outside the schema → emit canonical pair for the provider adapter to translate.

**Invariant:** Output tools are NEVER user-selectable individually — they enter the name set only wholesale via the internal folding; direct-output allowance is computed from model request parameters, not from the user's choice. Validation errors are loud and pre-flight.

**Probe:** `tests/test_capabilities.py::test_capability_can_inject_forcing_tool_choice_per_step` (:5696, per-step injection observed through settings) + `tests/test_agent.py::test_tool_choice_required_or_list_rejected_in_agent_run` (:12103). Coverage caveat: no dedicated unit file for `_tool_choice.py` itself; behavior pinned via agent/capability integration tests.

## Get live surrounding code
**Retrieve:**
```
search_graph --project mnt-hdd-utopia-inspo-pydantic-ai --query 'resolve_tool_choice ResolvedToolChoice'
```

## Verdict
**Adopt** the canonical-five-form resolver as THE boundary between user intent and provider wire values. **Adopt** pre-flight UserError validation against the live tool inventory. **Adapt** the input vocabulary to your settings surface. **Omit** nothing — one function, one contract.
