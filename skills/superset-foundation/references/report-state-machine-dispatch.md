<!-- capsule-v2 -->
# report-state-machine-dispatch — How does a celery tick pick exactly one execution state and refuse unknown ones?

**Source:** Apache Superset Apache-2.0 `master@9f505eb0cbbc39b78f512765d82fd63cf5ad70e6`; Codebase Memory `superset`. **Question:** When a scheduled alert/report task fires, how is the single next state class selected from the persisted `last_state`, and what happens when nothing matches?

## Crontab-driven state selection
**Path/Symbol:** `superset/commands/report/execute.py:ReportScheduleStateMachine` (:2064-2097).
**Signature:** `run(self) -> None` (decorated `@transaction()`); ctor takes `(task_uuid: UUID, report_schedule: ReportSchedule, scheduled_dttm: datetime, report_execution_context | None)`.
**Data Shape:** `states_cls = [ReportWorkingState, ReportNotTriggeredErrorState, ReportSuccessState]`; each class carries `current_states: list[ReportState]` and `initial: bool`. Selection input is the *persisted* `report_schedule.last_state`.

### Decisive source
```python
@transaction()
def run(self) -> None:
    for state_cls in self.states_cls:
        if (self._report_schedule.last_state is None and state_cls.initial) or (
            self._report_schedule.last_state in state_cls.current_states
        ):
            state_cls(
                self._report_schedule,
                self._scheduled_dttm,
                self._execution_id,
                self._report_execution_context,
            ).next()
            break
    else:
        raise ReportScheduleStateNotFoundError()
```

**Flow:** task entry → scan fixed class list in order → first class whose `current_states` contains the persisted `last_state` (or the `initial=True` class when `last_state is None`, i.e. first-ever run → ReportNotTriggeredErrorState) → instantiate with the same schedule/scheduled_dttm/execution uuid/execution context → call `.next()` → `break`. The for/else fires only when no class matched.
**Invariant:** Exactly one state runs per tick; dispatch is driven by durable DB state (`last_state`), never by task arguments, so a requeued/replayed task converges on the same state. Unknown persisted states fail loudly (`ReportScheduleStateNotFoundError`) instead of silently defaulting. `last_state=None` must map to the *initial* class, not to "no match".
**Probe:** `tests/unit_tests/commands/report/execute_test.py:3779-3789` (`test_state_machine_unknown_state_raises_not_found`) sets `schedule.last_state = "NONEXISTENT_STATE"` and asserts `sm.run()` raises `ReportScheduleStateNotFoundError`.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "superset", query: "ReportScheduleStateMachine run states_cls current_states initial", limit: 10 });
```

## Verdict
Adopt persisted-state-keyed dispatch over an ordered class registry with an explicit no-match error and a None→initial rule; adapt your own state enum/persistence; omit Superset's `@transaction()` decorator if your host scopes transactions elsewhere (but keep state writes atomic). Coverage: source range read directly at :2064-2097; direct test read at :3779-3789; both files `no_recorded_issue` / `metadata_match`.
