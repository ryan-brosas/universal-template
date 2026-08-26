<!-- capsule-v2 -->
# Coordinator assignment with validation feedback — How do you let an LLM pick workers for a batch of tasks without trusting it?

**Source:** CAMEL-AI/camel Apache-2.0 `master@13dc7a7d`; Codebase Memory `ext-camel`. **Question:** What is the retry/fallback contract that turns hallucinated assignee IDs into guaranteed valid assignments?

## Validate → feedback-retry → create-worker fallback
**Path/Symbol:** `camel/societies/workforce/workforce.py:Workforce._find_assignee` (:4042-4144), `_call_coordinator_for_assignment` (:3768-3881), `_handle_assignment_retry_and_fallback` (:3933-4009).
**Signature:** `async def _find_assignee(self, tasks: List[Task]) -> TaskAssignResult`; `_validate_assignments(assignments, valid_ids) -> Tuple[valid, invalid]`.
**Data Shape:** `TaskAssignResult{assignments: List[TaskAssignment]}`; `TaskAssignment{task_id, assignee_id, dependencies: List[str]}` with a before-validator accepting comma-separated string deps from sloppy LLMs (`_split_and_strip`, utils.py :186-199).

### Decisive source
```python
if invalid_ids:
    feedback = (f"VALIDATION ERROR: The following worker IDs are invalid: "
                f"{invalid_ids}. VALID WORKER IDS: {list(self._get_valid_worker_ids())}. "
                f"Please reassign ONLY the above tasks using these valid IDs.")
    prompt = prompt + f"\n\n{feedback}"
```

**Flow:** wait for workers with exponential backoff (0.05s ×1.5 capped 0.5s, 2.0s budget — timeout logs a warning and proceeds) → reset coordinator → single LLM call returns batch assignments → `_validate_assignments` splits on the real worker-id set → early return only when zero invalid AND zero unassigned → otherwise one retry call carrying the VALIDATION ERROR feedback for ONLY the failed tasks → still-invalid tasks get brand-new workers created on demand (`_handle_task_assignment_fallbacks`). Merge dedupes by task_id with retry results overriding valid ones (overlap logged). Empty/parse-failed coordinator responses return `TaskAssignResult(assignments=[])` instead of raising, which routes everything to fallback.
**Invariant:** LLM output is never posted directly — assignment validity is always checked against `_get_valid_worker_ids()` and every task leaves `_find_assignee` with an assignment, even if a worker had to be invented.
**Probe:** `grep -c 'VALIDATION ERROR' camel/societies/workforce/workforce.py` → 1; `grep -c '_handle_assignment_retry_and_fallback\|_validate_assignments' camel/societies/workforce/workforce.py` → 5 (two defs + three call sites).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-camel", query: "_find_assignee TaskAssignResult coordinator validate assignments fallback", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt validate→feedback-retry→provision-fallback as the general shape for any LLM-as-router decision. Adapt the feedback wording and fallback action. Omit structured-handler vs native `response_format` dual paths if your host has reliable native structured output.
