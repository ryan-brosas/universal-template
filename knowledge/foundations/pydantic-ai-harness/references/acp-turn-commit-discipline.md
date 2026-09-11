<!-- capsule-v2 -->
# ACP turn commit discipline — when may a turn's output become durable, and what must happen on every other exit path?

## Source / Question
`pydantic_ai_harness` (MIT) `main@76db3dec`; Codebase Memory project `pydantic-ai-harness`. **Question:** When an editor cancels a prompt mid-stream (or a usage limit trips, or the run raises), which state may be committed, which client-visible tool calls must be closed out, and how do you avoid orphaning a turn that is cancelled *inside* its own persistence step?

## Path / Symbol
`pydantic_ai_harness/experimental/acp/_adapter.py` — `PydanticAIACPAgent._run_turn` (:577–686); `_TurnState` (:128–142); `PydanticAIACPAgent.cancel` (:537–544); `PydanticAIACPAgent._fail_outstanding_tool_calls` (:688–700).

**Signature:**
```python
async def _run_turn(self, state: SessionState[AgentDepsT], prompt: list[PromptContentBlock],
                    user_content: list[UserContent]) -> schema.PromptResponse
async def cancel(self, session_id: str, **kwargs: object) -> None
async def _fail_outstanding_tool_calls(self, turn: _TurnState) -> None
```

**Data Shape:** `_TurnState` is per-turn bookkeeping created once per turn: `conn`, `session_id`, `cwd`, `approval_names: frozenset[str]`, three id sets (`started` = announced at least once across approval-resume passes; `denied` = rejected, result must be failed; `resulted` = reached a terminal status), and `updates: list[SessionUpdate]` — the transcript candidates appended only on commit. `cancel()` flips `state.cancel_requested` and `.cancel()`s `state.active_turn` if not done.

### Decisive source
```python
        except (asyncio.CancelledError, _TurnCancelled):
            # ... Shielded because an asyncio cancellation would otherwise abort the sends, and
            # live-only: a cancelled turn never commits its transcript.
            with anyio.CancelScope(shield=True):
                await self._fail_outstanding_tool_calls(turn)
            raise
        except UsageLimitExceeded as exc:
            # ... nothing is committed -- the turn rolls back to the prior state, like a
            # cancellation, and the response must not report uncommitted usage.
            await self._fail_outstanding_tool_calls(turn)
            return schema.PromptResponse(stop_reason=_usage_limit_stop_reason(exc))
        except Exception:
            await self._fail_outstanding_tool_calls(turn)
            raise

        state.history = history
        # Commit and persist this turn's updates alongside the history; a cancelled turn never
        # reaches here, so only committed turns are persisted.
        if self._session_store is not None:
            state.transcript.extend(turn.updates)
            try:
                await self._persist(state)
            except asyncio.CancelledError:
                # The turn is already committed: a cancel landing inside the store's save came
                # too late to roll anything back. ...
                stop_reason = 'cancelled'
```
And the closer (:695–699): `for tool_call_id in turn.started - turn.resulted:` → `session_update(... update=acp.update_tool_call(tool_call_id=..., status='failed'))` wrapped in `contextlib.suppress(Exception)`, sent directly (never recorded into `turn.updates`).

**Flow:** user turn → recorded into `turn.updates` up front ("a rolled-back turn does not persist its user message either") → resume loop over `run_stream_events` (approval pauses re-enter with `deferred_results`) → on finish: commit history + transcript, persist → response carries mapped stop reason + summed usage. Cancel/limit/error paths: close out outstanding tool calls first; cancel re-raises after a shielded closeout; limit converts to a normal limit stop reason with NO usage; generic errors re-raise after closeout. Late cancel during `_persist`: commit stands (warning "durable state is now behind"), but the spec-mandated `'cancelled'` stop reason is answered.

**Invariant:** Commit is all-or-nothing at turn granularity — exactly one of {nothing committed, everything committed}. Every announced-but-unfinished tool call reaches a terminal status on EVERY exit path, and those failure sends are best-effort + never part of the replayable transcript. A response must never report usage for state that was not committed.

**Probe:** `bash -c 'cd $REFERENCE_ROOT/pydantic-ai-harness && /tmp/harness-p6-venv/bin/python -m pytest "tests/experimental/acp/test_acp.py::TestCancellation::test_cancel_closes_out_in_flight_tool_calls" "tests/experimental/acp/test_acp.py::TestCancellation::test_cancelled_turn_with_a_store_persists_nothing" "tests/experimental/acp/test_persistence.py::test_cancel_landing_in_the_post_commit_save_commits_but_answers_cancelled" -q'` — in-flight tool call driven to `failed`; store keeps the pre-turn empty snapshot; post-commit cancel answers `'cancelled'` WITH usage and keeps history. (Executed this pass; see verification.md.)

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pydantic-ai-harness", query: "_run_turn cancelled turn never commits fail outstanding tool calls", limit: 5 });
```
Observed live: rank#1 `PydanticAIACPAgent._run_turn` (_adapter.py :577–686) and rank#3 `PydanticAIACPAgent.cancel` (:537–544); direct tests surface as callers of `_TurnState`.

## Verdict
**Adopt** the four-exit-path discipline for any long-running agent request surfaced over a protocol: shielded best-effort closeout of announced work, rollback semantics for cancel/limit, commit-only-on-finish, and the late-cancel-during-persist rule (commit stands, answer 'cancelled'). **Adopt** the started/denied/resulted triple-set to make "outstanding" cheap to compute across resume passes. **Adapt** stop-reason vocabulary to your wire protocol. **Omit** ACP/pydantic-ai specifics (anyio shields exist because `Task.cancel()` pierces them; keep whatever cancellation primitive your host uses). Caveat: none — behavior is directly test-pinned at this pin.
