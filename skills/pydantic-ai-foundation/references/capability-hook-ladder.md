<!-- capsule-v2 -->
# Capability hook ladder — before/wrap/after × validate/execute and where deferral is LEGAL

**Source:** pydantic-ai MIT `main@b3cdbc96796f0294f1ac6943cdba70d14af8a0ef`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai` (full mode, coverage clean). **Question:** What's the full middleware hook surface for tool/output lifecycles, and which positions may raise a deferral (CallDeferred/ApprovalRequired)?

## AbstractCapability hook surface
**Path/Symbol:** `pydantic_ai_slim/pydantic_ai/capabilities/abstract.py:AbstractCapability` (:162-1134; tool hooks :747-935, output hooks :937-1095, deferred handler :1099-1123); runner pairs in `_output.py:run_output_validate_hooks` (:126-173) / `run_output_process_hooks` (:176-220).
**Signature:** Per lifecycle stage X ∈ {run, node_run, model_request, tool_validate, tool_execute, output_validate, output_process}: `before_X(ctx, …)`, `wrap_X(ctx, …, handler)`, `after_X(ctx, …)`, plus error counterparts `on_X_error(ctx, …, error)` that **raise to propagate / return to suppress-and-recover**.
**Data Shape:** Tool hooks carry `(call: ToolCallPart, tool_def: ToolDefinition, args)` with args RAW pre-validation and VALIDATED after; output hooks carry `(output_context: OutputContext, output)`; wrap handlers are zero-arg-or-value-taking awaitables chained by the framework.

### Decisive source
```python
# abstract.py:757-767 — the legality rule stated on before_tool_validate
"""Modify raw args before validation.
Raise ModelRetry to skip validation and ask the model to redo the tool call.

A tool call can only be deferred once its arguments have been validated, so raising
CallDeferred or ApprovalRequired here is a UserError. Defer from after_tool_validate,
a tool's args_validator, or before_tool_execute."""

# abstract.py:866-885 — late deferral is accepted but pointless: side effects already happened
"""Modify result after execution.
...
Deferring from here is accepted but rarely what you want: the tool function has already run,
so its side effects happened and `result` is discarded."""

# _output.py:166-173 — outer wrapping converts ModelRetry/ValidationError to retry prompts
except ToolRetryError:
    raise  # Already wrapped, propagate
except (ValidationError, ModelRetry) as e:
    if wrap_validation_errors:
        raise _make_retry_prompt(e, run_context) from e
    raise
```

**Flow:** Validate phase: `before_tool_validate(raw)` → schema validation → `after_tool_validate(validated)` → execute phase: `before_tool_execute` → tool → `after_tool_execute(result)`; every stage has a wrap variant around it and an `on_*_error` recovery hook (control-flow exceptions — SkipToolValidation/SkipToolExecution/deferrals/ToolRetryError/ToolFailedError — do NOT reach error hooks). Output side mirrors this as validate (parse-only, structured modes) + process (all modes incl. text/image), with user output validators running INSIDE the process wrapper. Cancellation is TERMINAL at every level: hooks may observe CancelledError for cleanup but cannot recover a run/node to success (`after_node_run` doesn't even fire for cancelled nodes).
**Invariant:** Deferral legality ladder: ILLEGAL before validation completes (UserError naming the hook), legal at `after_tool_validate`/args_validator/`before_tool_execute`, accepted-but-useless after execution. Error-recovery hooks return-to-suppress; wrap handlers chain in capability order (first = outermost); ModelRetry raised directly from wrap BYPASSES its own error hook (control flow).
**Probe:** `tests/test_capabilities.py::test_validate_hook_cannot_defer_before_args_are_valid` (:11944), `::test_on_tool_validate_error_cannot_defer` (:11970 — exact UserError snapshot), `::test_hook_deferral_replaces_an_args_validator_deferral` (:11993).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "AbstractCapability before_tool_validate wrap_output_process on_model_request_error", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the symmetric before/wrap/after/on-error lattice with return-to-suppress semantics and the deferral-legality positions; adapt hook names/context objects to your host; omit realtime-session nuances if you have none. Caveat: source read at HEAD this session.
