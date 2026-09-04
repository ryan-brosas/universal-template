<!-- capsule-v2 -->
# Tool-call corrective feedback — bad tool calls become chat-history messages, not exceptions

**Source:** Microsoft semantic-kernel MIT `main@b39d95a34435f4c1d55dd00c86120ce118d847e1`; Codebase Memory `semantic-kernel`. **Question:** What should a kernel do when the model emits a malformed, unallowed, or wrongly-argued tool call — raise to the caller, or keep the conversation self-healing?

## Kernel.invoke_function_call validation ladder
**Path/Symbol:** `python/semantic_kernel/kernel.py:Kernel.invoke_function_call` (lines 326–463).
**Signature:** `async def invoke_function_call(self, function_call: FunctionCallContent, chat_history: ChatHistory, *, arguments: "KernelArguments | None" = None, execution_settings: "PromptExecutionSettings | None" = None, function_call_count: int | None = None, request_index: int | None = None, is_streaming: bool = False, function_behavior: "FunctionChoiceBehavior | None" = None) -> "AutoFunctionInvocationContext | None"`.
**Data Shape:** Input `FunctionCallContent` (name, plugin_name, function_name, index, raw JSON args); output is either an `AutoFunctionInvocationContext` (only when `terminate=True`) or `None`; every failure path appends one tool-role message to `chat_history`.

### Decisive source
```python
missing_params = required_param_names - received_param_names
unexpected_params = received_param_names - {param.name for param in function_to_call.parameters}
if missing_params or unexpected_params:
    msg_parts.append(f"Missing required argument(s): {sorted(missing_params)}.")
    msg_parts.append(f"Received unexpected argument(s): {sorted(unexpected_params)}.")
    msg = " ".join(msg_parts) + " Please revise the arguments to match the function signature."
    frc = FunctionResultContent.from_function_call_content_and_result(function_call_content=function_call, result=msg)
    chat_history.add_message(message=frc.to_chat_message_content())
    return None
```

**Flow:** Four failure classes each write a corrective tool message into history and return `None`: (1) missing name or name outside the behavior allowlist → `FunctionExecutionException` caught at 358; (2) function not resolvable via `get_function` → "not part of the provided tools … please try again"; (3) `FunctionCallInvalidArgumentsException`/`TypeError` while parsing JSON args → "Arguments must be in JSON format. Please try again."; (4) set-diff of required vs received params → sorted missing/unexpected names. Only after all validations pass does the auto-function-invocation filter stack run. If called with `function_behavior=None`, allowlist validation is skipped with only a debug log (350–356).
**Invariant:** A bad model tool call must never raise out of this method and never terminate the loop — the model gets exactly one tool-role reply it can correct on the next request round.
**Probe:** `python/tests/unit/kernel/test_kernel.py::test_invoke_function_call_with_continuation_on_malformed_arguments` (526–574) asserts the exact malformed-JSON text lands in `chat_history.add_message`; `::test_invoke_function_call_with_missing_or_unexpected_args` (577–626) asserts `result is None` plus the diff message; `::test_invoke_function_call_with_filters_blocks_unallowed_function` (629–657) pins allowlist blocking.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "semantic-kernel", query: "invoke_function_call FunctionExecutionException allowed", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the convert-to-tool-message-and-return-None pattern for any agent loop driven by provider tool calls — it is what makes retry-by-model work without host-side exception plumbing. Adapt the four message wordings to your product voice but keep them imperative and parameter-specific (sorted lists). Omit the `function_behavior=None` fail-open branch if your port requires an explicit allowlist always.
