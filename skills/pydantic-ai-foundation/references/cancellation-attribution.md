<!-- capsule-v2 -->
# First-party vs external cancellation attribution

## Source / Question
`pydantic_ai_slim/pydantic_ai/_cancel.py` — How does pydantic-ai distinguish a *first-party* cancellation (the app asked the run to stop → `RunCancelled`) from an *external* one (asyncio timeout/task-group/`Task.cancel()` → keep `CancelledError` propagating), even when they race? A porter must get this right or external cancels get swallowed as app-level outcomes.

## Path / Symbol
`pydantic_ai_slim/pydantic_ai/_cancel.py` — `CancellationToken` (42–89), `RunCancellation` (92–257), `RunBinding` (260–268), `provide_run_binding` (275–282), `take_run_binding` (285–293).

## Signature
```python
class RunCancellation:
    def bind(self, task: asyncio.Task | None = None) -> None      # at run start + each step boundary
    def cancel(self) -> None                                       # from any thread, idempotent
    def resolve(self) -> bool                                      # at outer edge: True → RunCancelled
    def release_issued(self) -> None                               # swallow cleanup
    def attach_token(self, token: CancellationToken) -> None
    def finish(self) -> None
```

## Data Shape
`_issued: dict[asyncio.Task, int]` — count of `Task.cancel()` calls this controller issued per driving task. `_owner`/`_loop` = current driving task + its loop. `_requested`/`_finished` sticky booleans. `_tokens: list[CancellationToken]`.

## Decisive source
`resolve()` (203–242): if not `_requested` → False. On Python <3.11 (no `Task.uncancel`) → True (documented degraded: first-party wins even if external raced). Otherwise pop the issued count for the current task, `Task.uncancel()` exactly that many times, and return `task.cancelling() == 0` — i.e. anything left on the counter was issued externally and takes precedence. `bind()` (121–152) re-syncs `_issued[task] = min(_issued[task], task.cancelling())` on 3.11+ so a user `uncancel()` doesn't leave a stale issuance.

## Flow / Invariant
1. First-party cancel = `task.cancel()` on the task driving the run, reusing the exact same teardown as external cancellation (streams closed, in-flight tools cancelled+drained, suspended jobs best-effort cancelled).
2. The controller **counts** every `Task.cancel()` it issues. On catching `CancelledError`, the outer edge consumes exactly that many via `Task.uncancel()` (mirroring `asyncio.timeout()`).
3. If `Task.cancelling()` is still positive afterward, an external cancellation raced in → it wins, `CancelledError` keeps propagating.
4. **Baseline-free** by design (unlike `asyncio.timeout()`): a cancellation already pending when the run started makes a first-party cancel resolve as external — conservative direction is "external wins".
5. **Thread-safety**: `cancel()` from another thread marshals via `loop.call_soon_threadsafe(self._deliver)`; `CancellationToken.cancel()` delivers synchronously on the run's own loop.
6. **Known residual window** (#7240): attribution counts cancellations, not identity — if user code catches a first-party cancel and calls `Task.uncancel()` itself, then an external cancel with matching count arrives before the next `bind()`, the clamp keeps a stale issuance and `resolve()` consumes the external cancel as first-party. Requires user code to uncancel a cancel it was handed.
7. `RunBinding` bridges the `AgentRunEvents` handle (which exists before its lazy background run) to the run; `take_run_binding()` consumes at most once so nested agent runs don't inherit the outer handle's binding.

## Probe (direct test)
`tests/test_run_cancellation.py` (1,827L): `test_external_cancellation_wins_race_with_first_party_cancel` (:1041), `test_external_cancellation_wins_when_it_arrives_first` (:1072), `test_external_cancellation_is_never_translated` (:810), `test_first_party_cancel_inside_asyncio_timeout_leaves_scope_intact` (:937), `test_cancel_before_bind_delivers_on_bind` (:736), `test_swallowed_and_uncancelled_request_redelivers_on_rebind` (:759), `test_release_issued_on_finished_task_is_noop` (:711), `test_run_cancellation_tracks_issuances_per_task` (:625).

## Retrieve
`search_graph --project mnt-hdd-utopia-inspo-pydantic-ai --query 'RunCancellation'` → `_cancel.RunCancellation.*` (bind 121–152, cancel 154–175, resolve 203–242).

## Verdict
**Adopt** the count/uncancel attribution pattern. It is the correct way to tell first-party from external cancellation under asyncio's cancellation model; a porter that skips the `uncancel` bookkeeping will mis-translate external cancels into app-level `RunCancelled`. Keep the Python 3.10 degraded path documented.
