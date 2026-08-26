<!-- capsule-v2 -->
# StepPersistence: settled-boundary snapshots, live-history stash for error rescue, tool-effect ledger

## Source / Question
`pydantic_ai_harness/step_persistence/_capability.py` (+ `_helpers.py`) — How do you persist an agent run so ANY crash leaves a continuable resume point — including a crash mid-tool-cycle — without double-saving the tail or losing the at-failure history? Porters snapshot only on success and discover the error path has nothing to resume from.

## Path / Symbol
`step_persistence/_capability.py` — `StepPersistence` (45–127), run-id resolution ladder (:82–126: explicit single-shot / `{agent_name}-{short-uuid}` fresh per run / ctx fallback; explicit REUSE raises ValueError because "the tool-effect ledger keys on `(run_id, tool_call_id)` and providers reuse deterministic tool-call ids, so a silent collision would erase the `unknown_after_crash` signal"), `from_spec` (:131–157 — unknown backend RAISES: "silently falling back to in-memory storage would turn a typo into accidental non-durability"), `wrap_run` ContextVar push (:221–236), `before_run` reuse check (:238–263), `after_run` fallback save (:266–299), `_stash_live_history` (:301–322), `on_run_error` (:343–374), tool hooks `before/after/on_tool_execute_error` (:411–504). `_helpers.py` — `is_provider_valid` (21–56), `continue_run/fork_run` (58–89), `annotate_tool_effect` (92–131).

## Signature
```python
async def _save_continuable_snapshot(ctx, messages, step_index, state: SnapshotState = 'complete')
# SnapshotState = 'complete' | 'interrupted'; default read path returns ONLY complete
def is_provider_valid(messages) -> bool  # no unsettled tool pairing; RetryPromptPart w/ tool_name resolves a call
```

## Data Shape
Three record families in the store: `RunRecord` (lineage: conversation_id, parent_run_id, agent_name), append-only `StepEvent`s (run/model-request/tool-call started/completed/failed with step_index + metadata), `ContinuableSnapshot` (messages + step_index + state) + `ToolEffectRecord` (status started/completed/failed, idempotency_key, effect_summary). Snapshots fold in the pending tool-return request AT the CallToolsNode boundary — durable the moment the tool completes.

## Decisive source
1. **Settled-boundary saves + fallback** (`after_run` :271–289): terminal CallToolsNode already saved the final history with the correct step_index ("by after_run ctx.run_step is reset to 0 -- re-saving would both duplicate the tail and stamp a misleading step_index"); save ONLY when history grew past the boundary counter (`snapshot_saved` ContextVar). This also covers streaming runs, which end through SetFinalResult and never hit the boundary.
2. **Error-path rescue via reference stash** (`_stash_live_history` :301–322): on_run_error's own RunContext holds the START-of-run list (UserPromptNode replaces it), so each boundary stashes `(ctx.messages, ctx.run_step)` BY REFERENCE into a ContextVar; leans on core invariant that rebind happens exactly once and later changes are in-place mutations — "If core ever rebinds mid-run again, this stash silently goes stale … tests pin the invariant so that surfaces as a test failure, not silent data loss." Re-stashed every boundary because the first still sees pre-rebind.
3. **Interrupted classification** (:343–368): the at-failure history is saved whenever it contains a model response ("a bare prompt equals restarting the run"), classified complete iff `is_provider_valid`, else `interrupted`; interrupted snapshots stay OFF the default read path — resuming one may re-execute pending tools, hence consult `list_unresolved_tool_effects` first.
4. **Tool-effect ledger**: before records status=started (the `unknown_after_crash` signal); after/error PRESERVE prior started_at/idempotency_key/effect_summary when writing the terminal record; `annotate_tool_effect` lets a TOOL BODY declare external writes mid-flight so an orchestrator can judge replay safety.
5. **Lineage auto-inference**: parent_run_id picked up from enclosing wrap_run's ContextVar — synchronous delegate runs inherit the orchestrator's run_id without manual threading; explicit value overrides for cross-process cases where ContextVars don't propagate.

## Flow / Invariant
wrap_run pushes run-id ContextVar → before_run registers lineage + rejects explicit-id reuse → boundaries emit events + save snapshots (fold pending returns) + restash live list → tool hooks maintain ledger preserving annotation fields → on error: save live at-failure history (state-classified) + run_failed event + re-raise → continue_run loads latest complete (or interrupted if asked) snapshot as message_history. Invariants: snapshot state is honest about tool-work settlement; explicit ids are single-shot; unknown backends fail loud; the ledger is keyed (run_id, tool_call_id).

## Probe (direct test)
`tests/step_persistence/test_step_persistence.py`: validity ladder :125–180 (unmatched call/duplicate/out-of-order/orphan retry all invalid), `test_continue_run_raises_when_no_snapshot` (:203), `test_interrupted_run_resumes_from_completed_tool_boundary` (:686), `test_run_stream_snapshot_keeps_the_final_response` (:715), `test_single_capability_instance_reused_gets_fresh_ids` (:797), `test_parent_run_id_inferred_via_contextvar` (:818), `test_tool_failure_records_failed_status_and_event` (:955), `test_visible_trail_no_false_continuation_point` (:1041); store round-trips incl. seq counters under unordered iteration :430–477.

## Retrieve
`search_graph --project pydantic-ai-harness --query 'StepPersistence ContinuableSnapshot is_provider_valid annotate_tool_effect'`

## Verdict
**Adopt** the three-part shape (event trail + state-classified snapshots + effect ledger) for any durable agent execution. **Adopt** reference-stash error rescue and preserve-annotation-on-terminal-record. **Adapt** backends behind the same StepStore protocol; keep fail-loud backend resolution.
