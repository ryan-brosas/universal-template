<!-- capsule-v2 -->
# Sandbox provider exec error mapping — how do you turn a provider SDK's exception zoo into a small retry-aware error taxonomy without misclassifying timeouts?

**Source:** OpenAI Agents Python MIT `main@fe45b415ee05`; Codebase Memory project `openai-agents-python` (MCP absent this pass — direct source+test reading fallback per AGENTS.md). **Question:** When a remote-sandbox provider (E2B, Modal) raises dozens of SDK-specific exception types mid-exec, how does the adapter decide retryable vs terminal vs timeout, preserve provider detail for diagnostics, and keep a nonzero command exit as DATA rather than an error?

## Provider exception classification ladder
**Path/Symbol:** `src/agents/extensions/sandbox/e2b/sandbox.py:` `_e2b_provider_retryability` (:94–111), `_raise_e2b_exec_error` (:114–160), `_e2b_retryable_error_types`/`_e2b_non_retryable_error_types`/`_e2b_timeout_error_types` (:543–577, best-effort name-based import), `_import_command_exit_exception` (:584–593), `_exec_internal` (:899–938), `_coerce_exec_timeout` (:775–781), `E2BSandboxTimeouts` (:584–605); `src/agents/extensions/sandbox/modal/sandbox.py:` `_modal_provider_retryability` (:184–199), `_modal_tar_persist_retryable` (:202–210), `_modal_exec_transport_error` (:213–241), `_exec_internal` (:792–838), `_modal_exception_types` (:133–146).
**Signature:** `def _e2b_provider_retryability(error: BaseException) -> tuple[bool | None, str | None]`; `def _raise_e2b_exec_error(exc, *, command, timeout, timeout_error_types) -> NoReturn`; `async def _exec_internal(self, *command: str | Path, timeout: float | None = None) -> ExecResult`.
**Data Shape:** Both providers classify over the WHOLE exception chain (`iter_exception_chain`). Result taxonomy: `ExecTransportError(command, context, cause, retryable)` for terminal/transport failures, `ExecTimeoutError(command, timeout_s, context, cause)` for timeouts, plain `ExecResult(stdout, stderr, exit_code)` for completed commands (including nonzero exits). `context` is a free dict carrying `provider_error`, `stdout`, `stderr`, `reason`, and (modal) `http_status`.

### Decisive source
```python
# e2b: one ladder walk over the chain — non-retryable, retryable, transient HTTP,
# then timeout — with the httpcore ReadTimeout special case:
for candidate in iter_exception_chain(error):
    if non_retryable_types and isinstance(candidate, non_retryable_types):
        return False, type(candidate).__name__
    if retryable_types and isinstance(candidate, retryable_types):
        return True, type(candidate).__name__
    status = getattr(candidate, "status_code", None) or getattr(candidate, "status", None)
    if isinstance(status, int) and status in TRANSIENT_HTTP_STATUS_CODES:
        return True, "transient_http_status"
...
is_timeout = exception_chain_contains_type(exc, timeout_error_types)
if not is_timeout and any(
    type(c).__name__ == "ReadTimeout" and type(c).__module__.startswith("httpcore")
    for c in chain
):
    ctx.setdefault("reason", "stream_read_timeout")
    is_timeout = True
if is_timeout:
    raise ExecTimeoutError(command=command, timeout_s=timeout, context=ctx, cause=exc) from exc
raise ExecTransportError(command=command, context=ctx, cause=exc, retryable=retryable) from exc
```
and the e2b rule that a command's nonzero exit is a RESULT, not a failure:
```python
if command_exit_exc is not None and isinstance(e, command_exit_exc):
    exit_code = int(getattr(e, "exit_code", 1) or 1)
    ...  # stdout/stderr harvested off the exception
    return ExecResult(stdout=..., stderr=..., exit_code=exit_code)
```

**Flow:** e2b `_exec_internal` joins argv with `shlex.join`, resolves envs (manifest envs override client base envs), passes `cwd` only when the workspace root is ready, unwraps the `sudo -u <user> --` prefix the base session inserts, coerces `timeout=None` to a 24 h sentinel (E2B treats None as its own 60 s default; the SDK's None must mean unbounded), then classifies any exception through `_raise_e2b_exec_error`. Provider exception TYPES are imported best-effort by name (`_e2b_exception_types`) so the adapter works against multiple SDK versions and in fake-based tests — an empty tuple simply disables that rung. Modal mirrors the same ladder shape with its own type lists (`ConnectionError/InternalError/InternalFailure/ServiceError` retryable; filesystem/auth/conflict errors non-retryable), adds `http_status` to context and promotes transient statuses to retryable inside `_modal_exec_transport_error`, and on `asyncio.TimeoutError` TERMINATES the sandbox and drops the handle (`self._sandbox = None; self.state.sandbox_id = None`) before raising `ExecTimeoutError` — a timed-out exec poisons the sandbox rather than leaving it half-alive. Modal's exec timeout is integer seconds (`ceil`, floored at `_DEFAULT_TIMEOUT_S`) because Modal's API granularity is 1 s. `_modal_tar_persist_retryable` reuses the same chain walk for tar persistence, with an explicit `SandboxError.retryable is False` veto.

**Invariant:** (1) Classification order is fixed: terminal types beat retryable types beat HTTP-status heuristics beat timeout probes — a terminal error is NEVER reported as a timeout even when the chain also contains a timeout type. (2) Provider detail survives into `context` (`provider_error`, stderr, reason) so operators see the SDK's message, not just the SDK's class. (3) A command that ran and exited nonzero is a successful exec RESULT; only the transport failing to run/observe the command is an error. (4) Timeout-type imports are version-tolerant: unknown SDK versions degrade to fewer rungs, never to crashes.

**Probe:** `tests/extensions/sandbox/test_e2b.py` — `test_e2b_exec_timeout_preserves_provider_details` (:2407, context carries provider_error + stderr), `test_e2b_exec_maps_httpcore_read_timeout_to_timeout_error` (:2445, reason=stream_read_timeout), `test_e2b_exec_maps_missing_sandbox_not_found_to_transport_error` (:2477, retryable is False), `test_e2b_exec_marks_rate_limit_retryable` (:2516), `test_e2b_exec_marks_deterministic_provider_errors_non_retryable` (:2551), `test_e2b_exec_transport_preserves_provider_details` (:2586); `tests/extensions/sandbox/test_modal.py` — `test_modal_pty_start_marks_typed_not_found_non_retryable` (:4535), `test_modal_pty_start_marks_typed_internal_failure_retryable` (:4568), `test_modal_pty_start_maps_timeout_failures` (:4635), `test_modal_pty_start_maps_modal_exec_timeout_failures` (:4663).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openai-agents-python", query: "provider retryability exec transport error timeout exception chain transient http status sandbox", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the fixed-order chain-walk ladder (terminal → retryable → transient-status → timeout) and the context-preserving error envelope for ANY provider SDK integration — it ports directly. Adopt the "nonzero exit is a result" rule for command executors. Adapt the type lists per provider and keep them name-imported so SDK version drift degrades gracefully. Omit the httpcore ReadTimeout special case unless your provider streams over httpcore. Coverage caveat: MCP absent this pass; Retrieve block is the canonical shape, not an executed call; all citations line-verified by grep against HEAD fe45b415ee05.
