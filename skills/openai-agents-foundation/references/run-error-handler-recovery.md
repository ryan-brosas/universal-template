<!-- capsule-v2 -->
# Run-error handler recovery — can a terminal run error (max turns / refusal / bad output) become a final output instead of an exception?

**Source:** OpenAI Agents Python MIT `main@fe45b415`; Codebase Memory `openai-agents-python`. **Question:** How are user-supplied per-error-kind handlers resolved, validated, and turned into a run result without weakening output contracts?

## Handler surface and strict result resolution
**Path/Symbol:** `src/agents/run_error_handlers.py:` `RunErrorData`/:17–26, `RunErrorHandlerInput`/:28–32, `RunErrorHandlerResult`/:35–40, `RunErrorHandlers`/:50–55; `src/agents/run_internal/error_handlers.py:` `build_run_error_data` (:113–136), `resolve_run_error_handler_result` (:226–262), `validate_handler_final_output` (:170–205), `create_message_output_item` (:208–223).
**Signature:** `async def resolve_run_error_handler_result(*, error_handlers: RunErrorHandlers[TContext] | None, error_kind: Literal["max_turns","model_refusal","invalid_final_output"], error, context_wrapper, run_data) -> RunErrorHandlerResult | None`.
**Data Shape:** `RunErrorData` snapshots input, new_items, history (input + converted new items), output (run items → input items via `run_item_to_input_item`, Nones skipped), raw_responses, last_agent. Handler may return `RunErrorHandlerResult | dict{"final_output","include_in_history"} | raw value | None`.

### Decisive source
```python
result = handler(handler_input)
if inspect.isawaitable(result): result = await result
if result is None: return None                      # no recovery → original exception propagates
if isinstance(result, RunErrorHandlerResult): return result
if isinstance(result, dict):
    if "final_output" in result:
        allowed_keys = {"final_output", "include_in_history"}
        extra_keys = set(result.keys()) - allowed_keys
        if extra_keys: raise UserError("Invalid run error handler result.")
        return RunErrorHandlerResult(**result)
    return RunErrorHandlerResult(final_output=result)   # bare dict IS the output
return RunErrorHandlerResult(final_output=result)
```

**Flow:** runner builds the snapshot (`build_run_error_data`) → looks up the kind-keyed handler (sync or async) → resolves the four return shapes above → structured agents validate the recovered value through the agent's own output schema (`dump_json` then `validate_json`, wrapper-dict payloads re-wrapped under `_WRAPPER_DICT_KEY`) — validation failures raise `UserError`, NOT `ModelBehaviorError`, so a broken handler cannot recurse into itself → text outputs become a real assistant item via `create_message_output_item` stamped with `FAKE_RESPONSES_ID`.
**Invariant:** handlers only convert errors they register for; returning None restores the default raising behavior; unknown dict keys fail loud; recovered structured outputs must satisfy the same schema as model-produced ones. Tracing note: `attach_generic_agent_error` (:75–110) only decorates spans for `Exception` subclasses (never cancellation), skips when a specific error is already on the span, redacts unless sensitive tracing is on, and never lets formatting failures propagate.
**Probe:** `tests/test_run_internal_error_handlers.py::test_resolve_run_error_handler_result_covers_async_and_validation_paths` (:87), `::test_validate_handler_final_output_raises_for_unserializable_data` (:75).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.get_code_snippet({ project: "openai-agents-python", qualified_name: "resolve_run_error_handler_result" }); // live resolution retrieved
```

## Verdict
Adopt kind-keyed handler registration, the four-shape resolution with strict dict keys, schema re-validation with UserError on failure, and fake-ID message synthesis for text recoveries. Adapt the error kinds to your loop's terminal taxonomy. Omit tracing-span specifics if you have no span tree. Coverage: no_recorded_issue at gen 2026-08-24T14:05:06Z.
