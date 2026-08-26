<!-- capsule-v2 -->
# Sandbox session lifecycle: shielded create with checkpointed teardown, terminal-vs-retryable error taxonomy, bounded best-effort cleanup

## Source / Question
`pydantic_ai_harness/modal_sandbox/_session.py` (+ `localstack/_container.py`) — How do you manage a remote sandbox/container as an async context manager so that cancellation can neither orphan a created sandbox nor hang forever on a wedged control plane, and so the model retries only failures retrying could fix? Porters either leak sandboxes on cancel or turn auth failures into infinite ModelRetry loops.

## Path / Symbol
`modal_sandbox/_session.py` — error taxonomy (16–44: `ModalSandboxError`(RuntimeError) → toolset converts to ModelRetry; `ModalSandboxTerminalError` propagates — "retrying cannot restore a missing sandbox or credentials"; Unavailable = terminated/expired; Auth = operator action), `ModalSandboxExecResult` (47–70: returncode `-1` = client deadline sentinel BUT plain 137 = SIGKILL read as timeout when the command consumed its whole window; `applied_timeout` = quantized whole-second deadline actually sent), shared defaults (18–22 so both public constructors cannot drift), `__aenter__` (222–265), `_open_sandbox` (267–290), `__aexit__` (292–330), `exec` task-group trio (430–546). `localstack/_container.py` — docker-CLI-driven container w/ health polling + `localhost.localstack.cloud` endpoint trick (:55–68).

## Signature
```python
async def __aenter__(self) -> Self:
    with anyio.CancelScope(shield=True):
        with anyio.move_on_after(_CREATE_TIMEOUT):        # bound the shield itself
            self._sandbox = await self._open_sandbox()
    if self._sandbox is None: raise ModalSandboxError('creation did not complete within …')
    try:
        await anyio.lowlevel.checkpoint()                 # honor pending cancellation
    except BaseException:
        await self.__aexit__(None, None, None)            # tear down what we just made
        raise

async def __aexit__(self, *args):
    with anyio.CancelScope(shield=True):
        try:
            if owned:
                with anyio.move_on_after(_TEARDOWN_TIMEOUT):   # EACH RPC bounded independently
                    await sandbox.terminate.aio(wait=True)
        finally:
            with anyio.move_on_after(_TEARDOWN_TIMEOUT):
                await sandbox.detach.aio()
```

## Data Shape
Owned vs ATTACHED sessions (`sandbox_id` set ⇒ attach): attach polls and refuses terminated sandboxes at enter; detach never terminates an attached sandbox. Exec result carries stdout/stderr + per-stream truncation flags + timed_out + applied_timeout. LocalStack: `--rm` container, `/_localstack/health` poll until ready, startup_timeout/poll_interval knobs.

## Decisive source
1. **Shield-with-deadline create** (:238–252): creation is shielded "so a normal cancellation arriving mid-create cannot drop the sandbox handle before we store it" — an owned sandbox would be orphaned (reaped only by its own server-side `sandbox_timeout`) because `__aexit__` would see no handle. The shield is BOUNDED by `move_on_after(_CREATE_TIMEOUT)` ("a shield with no deadline would hang forever", :100–104); after the deadline fires, fail rather than proceed handle-less.
2. **Checkpoint-after-create** (:255–264): the cancellation the shield suppressed is honored immediately after, and the just-created sandbox is torn down in the except path — no orphan between create and first use.
3. **Independent teardown deadlines** (:305–329): terminate and detach each get their OWN `move_on_after` — "a single shared deadline would cancel the detach the moment terminate hung"; detach runs in `finally` because it's Modal's recommended cleanup even when terminate failed. Both are exception-SILENT: "an exception from `__aexit__` would mask" the body's unwinding exception, and an already-gone sandbox is success not error.
4. **Shield scope honesty** (:249–251, :302–304): shields hold for anyio-scope cancellation only; a raw `asyncio.Task.cancel()` can still interrupt — the server-side `sandbox_timeout` is the documented backstop for that case.
5. **Timeout disambiguation** (:63–69): client-side deadline kill reports `-1`; server-side kill at the same deadline surfaces as exit 137 — both classified timed_out when the window was consumed, with `applied_timeout` exposing the quantized value actually sent.
6. **Error-to-model mapping**: direct ModalSandboxError → ModelRetry (transient); Terminal subclasses propagate to end the run (missing sandbox/auth can't be fixed by re-issuing).

## Flow / Invariant
enter: reuse guard (one context per session; cwd cache cleared on re-entry) → import check → shielded+bounded open (attach-poll or app-lookup+create) → None-check → checkpoint → handoff. exit: clear refs FIRST → owned? bounded terminate : skip → finally bounded detach. exec: task group races stream readers against wait_for_exit, cancelling siblings on first completion. Invariants: no path leaks an owned sandbox (shield+checkpoint+timeout backstop); cleanup never masks body exceptions; every wait has a deadline.

## Probe (direct test)
`tests/modal_sandbox/test_session.py`: `test_cancel_during_enter_terminates_created_sandbox` (:131), `test_teardown_bounded_when_terminate_hangs` (:98)/`…_detach_hangs` (:112), `test_terminate_failure_does_not_raise_and_still_detaches` (:73), `test_terminating_an_already_gone_sandbox_is_not_an_error` (:82), `test_error_exit_still_terminates` (:90), `test_attaches_detaches_but_does_not_terminate` (:147), `test_attach_to_terminated_sandbox_fails_at_enter` (:165). `tests/localstack/test_container.py` covers start/health/stop round trip.

## Retrieve
`search_graph --project pydantic-ai-harness --query 'ModalSandboxSession __aenter__ CancelScope shield checkpoint'`

## Verdict
**Adopt** the shield-bounded-create + checkpoint-teardown pattern for ANY remote resource opened inside a cancellable scope (VMs, browsers, cloud jobs). **Adopt** independent-cleanup-deadlines + mask-proof silent cleanup. **Adopt** the terminal-vs-retryable split at the error-class level so the model-facing retry policy falls out of the type system.
