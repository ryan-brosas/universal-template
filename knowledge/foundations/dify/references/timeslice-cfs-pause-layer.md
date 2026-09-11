<!-- capsule-v2 -->
# timeslice-cfs-pause-layer — How do you pause a running workflow when a tenant exhausts its compute slice?

**Source:** dify Apache-2.0 `main@8bdf702f`; Codebase Memory `ext-dify`. **Question:** What is the pattern for external, time-based suspension of an in-flight graph run?

## Class-level APScheduler job polling a CFS plan and sending PAUSE via command channel
**Path/Symbol:** `api/core/app/layers/timeslice_layer.py:TimeSliceLayer` (whole file, 91L); plan source `api/tasks/workflow_cfs_scheduler/cfs_scheduler.py:AsyncWorkflowCFSPlanScheduler.can_schedule`.
**Signature:** `__init__(cfs_plan_scheduler: CFSPlanScheduler)`; hooks `on_graph_start/on_event/on_graph_end`; `_checker_job(schedule_id)`.
**Data Shape:** `scheduler: ClassVar[BackgroundScheduler]` shared by ALL layer instances (started once); per-run `schedule_id = uuid4().hex`; interval = `plan.granularity` seconds; command payload `{"reason": SchedulerCommand.RESOURCE_LIMIT_REACHED}`.

### Decisive source
```python
class TimeSliceLayer(GraphEngineLayer):
    scheduler: ClassVar[BackgroundScheduler] = BackgroundScheduler()

    def _checker_job(self, schedule_id: str):
        try:
            if self.stopped:
                self.scheduler.remove_job(schedule_id)
                return
            if self.cfs_plan_scheduler.can_schedule() == SchedulerCommand.RESOURCE_LIMIT_REACHED:
                self.scheduler.remove_job(schedule_id)
                if not self.command_channel:
                    logger.exception("No command channel to stop the workflow")
                    return
                self.command_channel.send_command(
                    GraphEngineCommand(command_type=CommandType.PAUSE,
                                       payload={"reason": SchedulerCommand.RESOURCE_LIMIT_REACHED}))
        except Exception:
            logger.exception("scheduler error during check if the workflow need to be suspended")

    @override
    def on_graph_start(self):
        if self.cfs_plan_scheduler.plan.schedule_strategy == WorkflowScheduleCFSPlanEntity.Strategy.TimeSlice:
            self.schedule_id = uuid.uuid4().hex
            self.scheduler.add_job(lambda: self._checker_job(self.schedule_id),
                                   "interval", seconds=self.cfs_plan_scheduler.plan.granularity,
                                   id=self.schedule_id)

    @override
    def on_graph_end(self, error: Exception | None) -> None:
        self.stopped = True
        if self.schedule_id:
            self.scheduler.remove_job(self.schedule_id)
```

**Flow:** graph start → register interval job (only for TimeSlice strategy) → every granularity tick: stopped? remove : limit-reached? remove + send PAUSE command through the engine channel → engine pauses the run persistently → graph end always flips `stopped` and removes the job.
**Invariant:** Suspension is requested as a PAUSE COMMAND, never raised from inside node execution — persistence/resume machinery handles the rest; the checker swallows its own exceptions so a broken scheduler cannot kill the run it monitors; `command_channel` is assigned by the base layer class AFTER __init__ (hence the None check); one class-level scheduler serves all runs, jobs are keyed per-run.
**Probe:** `grep -c 'ClassVar\[BackgroundScheduler\]' core/app/layers/timeslice_layer.py` → 1; `grep -c 'CommandType.PAUSE' …` → 1; direct tests `tests/unit_tests/core/app/layers/test_timeslice_layer.py::test_checker_job_sends_pause_command`, `::test_checker_job_removes_when_stopped`, `::test_checker_job_handles_resource_limit_without_command_channel`.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-dify", query: "TimeSliceLayer checker job interval suspend workflow", limit: 10 });
```

## Verdict
Adopt "external watcher sends pause commands through the same channel as aborts" for quota/timeslice enforcement. Adapt the scheduler (APScheduler here) and the plan-check interface. Omit the CFS-plan entity specifics unless porting Dify's scheduling product.
