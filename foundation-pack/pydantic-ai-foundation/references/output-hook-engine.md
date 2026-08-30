<!-- capsule-v2 -->
# Output processor hook engine — validate/process ladders with error-hook recovery and wrap toggles

**Source:** pydantic-ai (MIT) `main@b3cdbc96796f0294f1ac6943cdba70d14af8a0ef`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** How do capability output hooks (before/wrap/after/on_error) run around output validation and processing, when does the on-error hook get its chance, and how do the streaming/streaming-off wrap flags change the behavior?

## _output.py hook engine
**Path/Symbol:** `pydantic_ai_slim/pydantic_ai/_output.py` — `_build_output_handlers` (75-104), `run_output_validate_hooks` (126-173), `run_output_process_hooks` (176-220), `run_none/image_process_hooks` (223-297), `run_output_with_hooks` (300-357), `execute_output_function` (360-395).
**Signature:** `run_output_validate_hooks(capability, *, run_context, output_context, output, do_validate, allow_partial=False, wrap_validation_errors=True)`; process variant mirrors it.
**Data Shape:** opaque per-invocation `state` flows validate→process through a closure; semantic value (not the dict envelope) is what hooks see; `OutputContext` carries mode/output_type/allows_* flags.

### Decisive source
```python
# VALIDATE ladder (structured only): before -> wrap -> [on_error] -> after
output = await capability.before_output_validate(...)
try:
    validated = await capability.wrap_output_validate(..., handler=do_validate)
except (ValidationError, ModelRetry) as e:
    if allow_partial:                      # streaming partial pass: NO recovery hook
        if wrap_validation_errors and isinstance(e, ValidationError): raise _make_retry_prompt(e,...)
        raise
    try:
        validated = await capability.on_output_validate_error(..., error=e)
    except (ValidationError, ModelRetry) as hook_error:
        raise _make_retry_prompt(hook_error, ...)   # error-hook failure also becomes retry

# PROCESS ladder (all modes): before -> wrap -> [on_error] -> after
try:
    result = await capability.wrap_output_process(..., handler=do_process)
except ToolRetryError: raise            # control flow, not an error
except ModelRetry: raise                # propagates to OUTER handler, skips on_error hook
except Exception as e:
    result = await capability.on_output_process_error(..., error=e)  # generic errors recoverable

# outer catch on BOTH ladders:
except ToolRetryError: raise                        # already wrapped
except (ValidationError, ModelRetry) as e:
    if wrap_validation_errors: raise _make_retry_prompt(e, ...) from e
    raise                                            # streaming: propagate raw for partial handling

# handlers close over state so the resolved union member survives validate->process
async def do_validate(data): nonlocal state; semantic, state = processor.hook_validate(data,...); return semantic
async def do_process(output): return await processor.hook_execute(output, state, ...)
```

**Flow:** structured outputs run the validate ladder first (real parsing), then the process ladder; text/none/image skip validation and run only process. Output validators (`@agent.output_validator`) are folded INTO `do_process` so they execute inside `wrap_output_process`, not after it. `execute_output_function` runs output functions plain and wraps `ModelRetry` → `ToolRetryError` only when asked.
**Invariant:** The `wrap_validation_errors=False` + `allow_partial=True` combination is exactly the streaming path — no retry wrapping, no on-validate-error recovery mid-stream. In the process ladder, `ModelRetry` deliberately bypasses the on-error hook (retry is model-facing control flow); only generic exceptions reach `on_output_process_error`. The outer wrapper is the single place that converts to `ToolRetryError`. The validate→process `state` handoff must stay in closure scope.
**Probe:** `tests/test_validation_context.py`, `tests/test_agent.py::test_output_validator` suites, and streaming partial paths in `tests/test_streaming.py` pin the wrap/recovery matrix.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "run_output_validate_hooks run_output_process_hooks on_output_process_error ToolRetryError", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the dual-ladder structure and the ModelRetry-skips-recovery-hook rule; adapt the hook names to your middleware vocabulary; omit the pydantic ValidationError coupling by mapping it to your validation exception type. Complements `output-semantic-envelope.md` (what hooks see) — this capsule is the control flow around it. Coverage clean.
