<!-- capsule-v2 -->
# Recorded tool-result unwrap — replayed control-flow wrappers must surface as their wrapped values

## Source / Question
`pydantic_ai_slim/pydantic_ai/durable_exec/_toolset.py` @ `main@b3cdbc96` (MIT); Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** Engines that replay recorded durable-unit outputs (DBOS step recovery, Prefect task caches) may hold outputs recorded BEFORE the unit started wrapping control-flow exceptions (ToolFailed, ModelRetry, ApprovalRequired…) as VALUES — how do you normalize both recording eras without double-unwrapping raw results? A porter will treat every stored value as a plain result and lose retry/approval semantics on recovery.

## Path / Symbol
`durable_exec/_toolset.py` — `unwrap_recorded_tool_call_result` (:265–278), `resolve_tool_durable_config` (:281–296), `DurableToolsetBase` (:299+).

## Signature
```python
def unwrap_recorded_tool_call_result(result: Any) -> Any:
    if isinstance(result, (_ToolReturn | _ToolContentResult | _ApprovalRequired
                           | _CallDeferred | _ModelRetry | _ToolFailed)):
        return unwrap_tool_call_result(result)
    return result
def resolve_tool_durable_config(tool, tool_name: str,
    fallback_config: Mapping[str, ToolConfig], *, metadata_key: str,
    config_type_label: str) -> ToolConfig
```

## Data Shape
The wrapper set is exactly the five control-flow carriers a tool body may raise-as-value (`_ToolReturn`, `_ToolContentResult`, `_ApprovalRequired`, `_CallDeferred`, `_ModelRetry`, `_ToolFailed`). Anything else — including genuinely-plain return values from the old recording era — passes through untouched. `resolve_tool_durable_config` resolves per-tool config: explicit tool metadata under `metadata_key` first (`False` = opted out; non-dict non-None = loud UserError), else per-toolset fallback by name, else `{}`.

### Decisive source — era-tolerant unwrap (:265–278)
```python
"""Engines that replay recorded durable-unit outputs (DBOS step recovery, Prefect task caches)
may hold outputs recorded before the unit wrapped control-flow exceptions as values; those
recordings are the raw tool result and are returned unchanged."""
if isinstance(result, (_ToolReturn | _ToolContentResult | _ApprovalRequired | _CallDeferred
                       | _ModelRetry | _ToolFailed)):
    return unwrap_tool_call_result(result)
return result
```
Consumers: every DBOS/Prefect dynamic/function/MCP toolset's call path ends with `unwrap_recorded_tool_call_result(await step(...))`. `DurableToolsetBase` mirrors `DurableModel`: engine specifics live in segment callables each running one operation inside the engine's unit; `id` delegates to the wrapped toolset; lifecycle `'enter-outside-durable'` makes for_run/for_run_step no-ops outside containers.

**Flow:** durable unit returns → recorded payload inspected → carrier-shaped values unwrapped to their inner result/exception semantics → plain values returned as-is → downstream sees identical shape whether the output was freshly raised or recovered from an old-format cache.

**Invariant:** Unwrapping is whitelist-driven (only known carriers), never heuristic; config metadata is validated loudly (`False` opt-out honored; wrong type raises naming the expected label).

**Probe:** Direct tests live in the engine suites via replay paths — `tests/test_dbos.py::test_dbos_agent_run_in_workflow_with_runtime_function_toolset` (:1335) exercises the step-record→unwrap round trip with real tool results; `tests/test_prefect.py` task-cache recovery paths exercise the cached-era branch. No isolated unit test at this HEAD — coverage caveat noted.

## Get live surrounding code
**Retrieve:**
```
search_graph --project mnt-hdd-utopia-inspo-pydantic-ai --query 'unwrap_recorded_tool_call_result resolve_tool_durable_config DurableToolsetBase'
```

## Verdict
**Adopt** the whitelist unwrap and three-tier config resolution for any replay/cache layer over tool results. **Adapt** the carrier union to your host's control-flow vocabulary. **Omit** the segment-callable scaffolding if you have one engine, not three.
