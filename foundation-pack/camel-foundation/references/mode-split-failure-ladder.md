<!-- capsule-v2 -->
# Mode-split failure ladder — When a worker reports FAILED, in what order do retry limits, halt flags, and recovery strategies apply?

**Source:** CAMEL-AI/camel Apache-2.0 `master@13dc7a7d`; Codebase Memory `ext-camel`. **Question:** What is the exact decision ladder from failure event to (retry | reassign | replan | decompose | create_worker | halt)?

## Nine-rung ladder, cheapest checks first
**Path/Symbol:** `camel/societies/workforce/workforce.py:Workforce._handle_failed_task` (:4642-4924), `_mark_task_permanently_failed` (:4926-4939).
**Signature:** `async def _handle_failed_task(self, task: Task) -> bool` — True = halt workforce.
**Data Shape:** Reads/writes `task.failure_count`, `FailureHandlingConfig(max_retries=3 ge=1, enabled_strategies: Optional[List[RecoveryStrategy]]=None, halt_on_max_retries=True)`; strategy enum `RETRY/REPLAN/DECOMPOSE/CREATE_WORKER/REASSIGN`.

### Decisive source
```python
if task.failure_count >= max_retries:
    if self.mode == WorkforceMode.PIPELINE:
        await self._mark_task_permanently_failed(task)
        await self._post_ready_tasks(); return False   # pipeline never halts
    if not self.failure_handling_config.halt_on_max_retries:
        await self._mark_task_permanently_failed(task); return False
    return True                                        # AUTO_DECOMPOSE halts
if len(self._pending_tasks) > MAX_PENDING_TASKS_LIMIT:  # 20, anti-explosion
    return True
```

**Flow:** increment `failure_count` → rungs in order: (1) max-retries × mode/halt-config split above; (2) pending>20 → halt; (3) PIPELINE retry = reset `state=OPEN`, re-append to `_pending_tasks` (no LLM); (4) `enabled_strategies==[]` → permanent fail, no recovery; (5) exactly one enabled strategy → build `TaskAnalysisResult` directly, SKIP LLM analysis; (6) else LLM analysis via `_analyze_task(for_failure=True)`. Before ANY strategy application: preserve `original_assignee = self._assignees.get(task.id)` (None ⇒ log "bug in the task assignment chain", fail task, return halt flag), then `await self._channel.archive_task(id)` + `_cleanup_task_tracking(id)` — cleanup happens only AFTER the assignee is captured. Strategy application is centralized in `_apply_recovery_strategy` (:1828-2030): RETRY reposts to original assignee; REPLAN swaps `task.content` then reposts; REASSIGN calls `_find_assignee([task])` and if the same worker comes back AND `len(self._children)>1`, appends "Note: Previous worker ... had quality issues" to content and re-asks; DECOMPOSE inserts subtasks at queue head via `_pending_tasks.extendleft(reversed(subtasks))` and returns True (caller adds parent to completed); CREATE_WORKER mints a worker for the task. Strategy exceptions are caught by callers and converted into completed-task + halt-flag decisions, never left to propagate.
**Invariant:** The assignee must be read BEFORE archive/cleanup erases it — every recovery path that reposts needs the preserved id. And `enabled_strategies` has THREE states with different semantics: None=all (LLM analysis), []=none (immediate fail), [x]=single (no LLM).
**Probe:** `grep -c 'original_assignee' camel/societies/workforce/workforce.py` → 18; `grep -n 'MAX_PENDING_TASKS_LIMIT = ' camel/societies/workforce/workforce.py` → `128:MAX_PENDING_TASKS_LIMIT = 20`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-camel", query: "_handle_failed_task RecoveryStrategy enabled_strategies halt_on_max_retries", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the ladder ordering (cheap counters → config short-circuits → LLM last) and the preserve-assignee-before-cleanup invariant wholesale. Adapt strategy set to host actions. Omit the quality-eval twin of this ladder (`_listen_to_channel` DONE branch :5522-5710) unless you also port quality gates — same validation/fallback block appears there twice.
