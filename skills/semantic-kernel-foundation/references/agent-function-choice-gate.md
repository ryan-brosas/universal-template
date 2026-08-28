<!-- capsule-v2 -->
# Agent function-choice gate — only Auto(auto_invoke=True) is legal; tool view = SDK tools + filtered kernel metadata

**Source:** Microsoft semantic-kernel MIT `main@b39d95a34435f4c1d55dd00c86120ce118d847e1`; Codebase Memory `semantic-kernel`. **Question:** Which function-choice behaviors may an agent accept, and how is the provider tool view assembled when the run loop — not the connector — owns invocation?

## _validate_function_choice_behavior + _get_tools
**Path/Symbol:** `python/semantic_kernel/agents/open_ai/assistant_thread_actions.py:AssistantThreadActions._validate_function_choice_behavior` (875–912) and `_get_tools` (913–950); gate call sites at 198 (invoke) and 433 (invoke_stream).
**Signature:** `def _validate_function_choice_behavior(function_choice_behavior: FunctionChoiceBehavior | None) -> None`; `def _get_tools(cls, agent, kernel, tools_override=None, function_choice_behavior=None) -> list[dict[str, str]]`.
**Data Shape:** The gate is fail-fast: it runs BEFORE run creation, at the top of both invoke paths. Valid filter keys are exactly `{excluded_plugins, included_plugins, excluded_functions, included_functions}`.

### Decisive source
```python
if function_choice_behavior is None:
    return
if function_choice_behavior.type_ != FunctionChoiceType.AUTO:
    raise AgentInvokeException(
        f"FunctionChoiceBehavior with type '{function_choice_behavior.type_}' is not supported for agent "
        "invocations. Use FunctionChoiceBehavior.Auto(filters=...) ...")
if not function_choice_behavior.auto_invoke_kernel_functions:
    raise AgentInvokeException(
        "FunctionChoiceBehavior.Auto(auto_invoke=False) is not supported for agent invocations. "
        "The agent run loop manages tool invocation; disabling auto_invoke is not compatible.")
valid_filter_keys: set[str] = {"excluded_plugins", "included_plugins",
                               "excluded_functions", "included_functions"}
if function_choice_behavior.filters is not None:
    if not function_choice_behavior.filters:
        raise AgentInvokeException("FunctionChoiceBehavior filters must not be empty. ...")
    unknown_keys = {str(k) for k in function_choice_behavior.filters} - valid_filter_keys
    if unknown_keys:
        raise AgentInvokeException(f"Unknown filter key(s): {sorted(unknown_keys)}. ...")

# tool-view assembly
source_tools = tools_override if tools_override is not None else agent.definition.tools
for tool in source_tools:
    if isinstance(tool, CodeInterpreterTool): tools.append({"type": "code_interpreter"})
    elif isinstance(tool, FileSearchTool):    tools.append({"type": "file_search"})
if function_choice_behavior is not None and not function_choice_behavior.enable_kernel_functions:
    funcs = []
elif function_choice_behavior is not None and function_choice_behavior.filters:
    funcs = kernel.get_list_of_function_metadata(function_choice_behavior.filters)
else:
    funcs = kernel.get_full_list_of_function_metadata()
tools.extend([kernel_function_metadata_to_function_call_format(f) for f in funcs])
```

**Flow:** Because the agent's run loop (not the connector's auto-invoke machinery) executes tool
calls, only `Auto(auto_invoke=True)` makes sense: `Required` and `NoneInvoke` change who invokes,
and `Auto(auto_invoke=False)` would advertise functions the loop never runs — all three are
rejected up front with `AgentInvokeException`. `None` is legal (no kernel functions). Filters are
validated against the exact four-key set: empty filters are an error (ambiguous between "all"
and "none"), unknown keys are an error. Tool view = SDK-level tools (`tools_override` REPLACES
`agent.definition.tools` when provided; mapped to `{"type": ...}` dicts) plus kernel function
metadata — none when `enable_kernel_functions=False`, filtered when filters are set, full
otherwise — projected through `kernel_function_metadata_to_function_call_format`.
**Invariant:** The gate runs before any network call, so an illegal behavior can never reach run
creation. The Assistant family owns this gate; the Responses family skips it (its loop takes
`function_choice_behavior` as a required argument and does not validate the type). Filter
semantics reuse the kernel's tool-view dispatch (see tool-view-metadata-dispatch): included and
excluded are mutually exclusive per level, matching is by fully-qualified name.
**Probe:** `python/tests/unit/agents/openai_assistant/test_assistant_thread_actions.py::test_validate_function_choice_behavior_rejects_required` (862), `_accepts_auto` (868), `_rejects_none_invoke` (873), `_accepts_none` (879), `_rejects_auto_invoke_false` (884), `_rejects_empty_filters` (890), `_rejects_unknown_filter_keys` (898), `_accepts_valid_filters` (907); `test_get_tools_with_tools_override` (914), `_with_fcb_filters` (934), `_with_fcb_disable_kernel_functions` (962); end-to-end `test_invoke_raises_for_non_auto_fcb` (1144), `test_invoke_stream_raises_for_non_auto_fcb` (1162).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "semantic-kernel", query: "_validate_function_choice_behavior _get_tools kernel_function_metadata_to_function_call_format get_list_of_function_metadata", limit: 10, fields: ["signature", "name", "file"] });
```
(Not executable this pass — MCP surface absent; query kept byte-for-byte for the next connected pass.)

## Verdict
Adopt: fail-fast validation of who-invokes semantics before any run/resource creation, and the two-source tool view (server-side tools + filtered kernel functions) with tools_override replacing (not merging) the definition. Adapt the legal-behavior set to your run-loop ownership model — if your connector owns invocation instead, the kernel's AutoInvokeKernelFunctions path applies and this gate is wrong. Omit the gate entirely when your agent plane has no function-choice surface.
