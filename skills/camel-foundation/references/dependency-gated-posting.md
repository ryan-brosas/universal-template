<!-- capsule-v2 -->
# Dependency-gated posting — When is a pending task actually posted to the channel, and what separates pipeline from DAG semantics?

**Source:** CAMEL-AI/camel Apache-2.0 `master@13dc7a7d`; Codebase Memory `ext-camel`. **Question:** How does the supervisor decide a task's dependencies are satisfied, and how does failure propagate differently per mode?

## Assign-then-post sweep with per-mode completion predicates
**Path/Symbol:** `camel/societies/workforce/workforce.py:Workforce._post_ready_tasks` (:4397-4640), `_update_task_dependencies_from_assignments` (:4011-4040).
**Signature:** `async def _post_ready_tasks(self) -> None`.
**Data Shape:** `_task_dependencies: Dict[task_id, List[dep_id]]`, `_assignees: Dict[task_id, worker_id]`, `completed_tasks_info = {t.id: t.state for t in self._completed_tasks}` precomputed for O(1) lookup.

### Decisive source
```python
if self.mode == WorkforceMode.PIPELINE:
    should_post_task = True          # deps complete (success OR failure)
else:
    all_deps_done = all(completed_tasks_info[d] == TaskState.DONE
                        for d in dependencies)
    should_post_task = all_deps_done  # AUTO_DECOMPOSE needs success
```

**Flow:** Step 1 select unassigned tasks (PIPELINE: id not in `_assignees`; other modes: no `_task_dependencies` entry AND not flagged `_needs_decomposition`) → batch `_find_assignee` → record assignment + TaskAssignedEvent. Step 2 for each assigned-but-unposted task: skip if already in channel with an `assigned_worker_id` (duplicate-post guard via `channel.get_task_by_id`) → if ALL deps present in completed map, apply the mode predicate above; AUTO_DECOMPOSE additionally splits failed deps into retry-potential (`failure_count < max_retries`) vs permanently-failed and fails the downstream task only when EVERY dep is permanent. Step 3 remove posted tasks from `_pending_tasks`, tolerating `ValueError` (another path removed them). Dependency ID→object resolution happens in `_update_task_dependencies_from_assignments` over a merged map of completed+pending+batch tasks, silently dropping unknown dep ids.
**Invariant:** "Completed" means terminal (DONE or FAILED) for the posting gate; success is enforced separately by mode. A missing dependency keeps the task pending forever rather than failing it.
**Probe:** `grep -c 'should_post_task' camel/societies/workforce/workforce.py` → 4.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-camel", query: "_post_ready_tasks dependencies PIPELINE AUTO_DECOMPOSE", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-phase assign→post sweep and the mode-split predicate (error-propagating pipelines vs success-only DAGs). Adapt WorkforceMode to your orchestration modes. Omit pipeline builder plumbing (`pipeline_add/fork/join` :886-1176) — it is authoring sugar over the same fields.
