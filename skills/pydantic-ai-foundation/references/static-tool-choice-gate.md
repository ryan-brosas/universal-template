<!-- capsule-v2 -->
# Static tool_choice gate — required/list raise on the baseline, callables are trusted

## Source / Question
`pydantic_ai_slim/pydantic_ai/agent/__init__.py` (:1485–1508) + `settings.py` `ToolChoice` docs (:240–278) @ `main@b3cdbc96` (MIT); Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** `'required'` or a tool-name list as `tool_choice` forces a tool call every step — which makes an agent loop unable to EVER produce a final response (output tools are excluded) — yet per-step variation ("force a tool on the first step only") is legitimate. Where do you draw the static/dynamic line and enforce it? A porter will validate at the provider layer (too late, inconsistent) or ban the values outright (kills legitimate use).

## Path / Symbol
`agent/__init__.py` — baseline computation + UserError; `settings.py` — `ToolChoice = ToolChoiceScalar | list[str] | ToolOrOutput | None`, `ToolOrOutput(function_tools=[...])` escape hatch, and the documented rule that capability `get_model_settings()` CALLABLES "are trusted to adapt across steps".

## Signature
```python
baseline_settings: ModelSettings | None = model_used.settings
if not callable(agent_model_settings):                       # agent-level callable layer skipped
    baseline_settings = merge_model_settings(baseline_settings, agent_model_settings)
if not callable(run_model_settings):                         # run-level callable layer skipped
    baseline_settings = merge_model_settings(baseline_settings, run_model_settings)
if baseline_settings:
    tool_choice = baseline_settings.get('tool_choice')
    if tool_choice == 'required' or isinstance(tool_choice, list):
        raise exceptions.UserError(
            f'`tool_choice={tool_choice!r}` prevents the agent from producing a final response '
            f'because output tools are excluded. Use `ToolOrOutput` to combine specific function '
            f"tools with output capability, return a callable from a capability's "
            f'`get_model_settings()` to vary `tool_choice` per step, ...')
```

## Data Shape
Valid static values: None/'auto'/'none'; banned static values: 'required', list[str]; `ToolOrOutput` re-enters legally by pairing named function tools WITH output tools/text. Callable settings layers (any of agent-level, run-level, capability-supplied) make the whole merged value dynamic and skip validation entirely.

### Decisive source — validate the BASELINE only (:1490–1493)
```python
# Validate `tool_choice` on the static baseline. Callable layers (agent-level callable,
# run-level callable, capability-supplied) may inject `'required'` or `list[str]` per-step
# and are trusted to adapt across steps; static dict values would lock every step into a
# tool call and prevent the agent from producing a final response.
```
Note the merge order subtlety: `run_model_settings` is only folded when there is NO override (`model_settings if model_settings_override is None else None`, :1488), so the checked baseline is exactly what will hit the wire statically.

**Flow:** run() start → merge non-callable layers into baseline → scan `tool_choice` → banned static value raises UserError with THREE remedies (ToolOrOutput / capability callable / direct.model_request for single-shot) → otherwise proceed; dynamic injection stays unpoliced by design.

**Invariant:** Legality of forced-tool-choice depends on TIME-VARIANCE, not value: static=illegal, callable=trusted. Enforce once at run entry where all static sources have merged, with an error message naming every legal alternative.

**Probe:** `tests/test_agent.py::test_tool_choice_required_or_list_rejected_in_agent_run` (:12096–12116 — parametrized 'required'/['get_weather'], matches 'prevents the agent from producing a final response').

## Get live surrounding code
**Retrieve:**
```
search_graph --project mnt-hdd-utopia-inspo-pydantic-ai --query 'test_tool_choice_required_or_list_rejected_in_agent_run'
```

## Verdict
**Adopt** the baseline-only validation gate and the static-vs-callable trust boundary for any setting that can deadlock your own loop. **Adapt** the banned-value set to your schema. **Omit** nothing.
