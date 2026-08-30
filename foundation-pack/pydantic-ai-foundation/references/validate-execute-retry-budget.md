<!-- capsule-v2 -->
# Validate/execute split & retry budget — why does ToolManager separate validation from execution, and which failures consume the retry budget?

**Source:** pydantic-ai MIT `main@b3cdbc96796f0294f1ac6943cdba70d14af8a0ef`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai` (full mode, coverage clean). **Question:** What is the exact contract of `validate_tool_call` → `execute_tool_call`, and what are the rules for when a failure counts against retries vs. surfaces raw?

## ValidatedToolCall as the seam
**Path/Symbol:** `pydantic_ai_slim/pydantic_ai/tool_manager.py:ValidatedToolCall` (55–94), `ToolManager.validate_tool_call` (604–687), `:execute_tool_call` (689–729) + `_execute_tool_call_impl` (933–987), budget accounting in `_make_validation_failure` (564–602) / `_check_max_retries` (256–265).
**Signature:** `validate_tool_call(call, *, approved=False, metadata=None, wrap_validation_errors=True) -> ValidatedToolCall`; `execute_tool_call(validated, *, wrap_validation_errors=True) -> Any`.
**Data Shape:** `ValidatedToolCall{call, tool|None, ctx, args_valid, validated_args|None, validation_error|None, deferral|None}` — one object answers "did args validate", "what should the model see if not", and "was a deferral requested with valid args". `failed_tools`/`succeeded_tools` sets carry per-step state; `ctx.retries` carries cross-step counts.

### Decisive source
```python
# tool_manager.py:256-265 — >= on purpose: a negative budget must fail fast, not loop
def _check_max_retries(self, name, max_retries, error):
    # `>=` rather than `==` so a negative budget raises immediately instead of looping forever
    if self.ctx.retries.get(name, 0) >= max_retries:
        raise UnexpectedModelBehavior(...) from error

# :582-593 — the ONE free availability refusal per tool, per RUN (not per step)
if isinstance(error, _ToolUnavailable) and name not in self.availability_refused:
    self.availability_refused.add(name)
else:
    self._check_max_retries(name, max_retries, cause)
    self.failed_tools.add(name)
```

**Flow:** Validation resolves the tool (unknown name → `ModelRetry`; known-but-not-yet-available → `_ToolUnavailable`) → builds a per-call RunContext (`tool_name`, `retry`, `max_retries`, `approved`, metadata) → runs schema+custom validator + capability validate-hooks → returns success/failure/deferral WITHOUT executing. Execution raises any carried deferral first (`args_validator` deferrals re-surface at exactly the same boundary as tool-body ones), refuses external kinds, runs execute-hooks, then the raw call; `SkipToolExecution` converts to a synthetic result while still charging a tool call.
**Invariant:** Budget rules are asymmetric by design: `ValidationError | ModelRetry` consume retry budget; `ToolFailed` wraps WITHOUT consuming; the FIRST `_ToolUnavailable` refusal per tool is free (charging it would make one act of model disobedience fatal on default budget 1) and lives in a run-scoped set so step rollover can't refill it. `wrap_validation_errors=False` leaves ALL retry-budget state untouched (raw errors propagate) — that's how nested/sandboxed callers avoid spending the agent's budget. Retry counts roll over via `for_run_step`: keep failed tools' counts (+1), drop succeeded tools'.
**Probe:** `tests/test_usage_limits.py` + `tests/test_run_context_usage_limits.py` pin usage/retry behavior; `tests/test_tools.py` exercises validator paths.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "ValidatedToolCall _make_validation_failure availability_refused for_run_step SkipToolExecution", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the validate/execute split with the carrier object, the free-first-availability-refusal rule, and raw-error mode leaving budgets untouched; adapt hook names to your framework's extension points; omit output-tool-specific dual budgets unless you port output tools too. Caveat: none — full file read this session.
