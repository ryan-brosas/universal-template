<!-- capsule-v2 -->
# Quality-gate recovery twin — How does a DONE-but-low-quality task get a second chance without burning the retry budget?

**Source:** CAMEL-AI/camel Apache-2.0 `master@13dc7a7d`; Codebase Memory `ext-camel`. **Question:** What is the exact flow from `_analyze_task(for_failure=False)` to a recovery strategy, and where does the retry limit soften?

## Score gate → softened limit → strategy validation → archive+recover
**Path/Symbol:** `camel/societies/workforce/workforce.py:Workforce._listen_to_channel` DONE branch (:5498-5710), `_analyze_task` (:1645).
**Signature:** `quality_retry_limit = max(1, self.failure_handling_config.max_retries - 1)`; `TaskAnalysisResult{reasoning, recovery_strategy, modified_task_content, quality_score?, issues?, is_quality_evaluation?}`.
**Data Shape:** `enabled_strategies == []` short-circuits BEFORE any LLM call (log "quality check skipped - no recovery strategies"); otherwise one structured LLM evaluation.

### Decisive source
```python
if returned_task.failure_count >= quality_retry_limit:   # max(1, max_retries-1)
    ... await self._handle_completed_task(returned_task); continue   # accept anyway
...
returned_task.failure_count += 1
returned_task.state = TaskState.FAILED
# validate/fallback recovery_strategy against enabled_strategies
original_assignee = self._assignees.get(returned_task.id)
await self._channel.archive_task(returned_task.id)
self._cleanup_task_tracking(returned_task.id)
is_decompose = await self._apply_recovery_strategy(
    returned_task, quality_eval, original_assignee)
```

**Flow:** DONE arrives → insufficiency veto first (`is_task_result_insufficient`, separate capsule) → strategies disabled ⇒ complete as-is → LLM quality eval (`_analyze_task(for_failure=False)`) → score insufficient: if `failure_count >= max(1, max_retries-1)` ACCEPT the low-quality result (retry limit reached — deliberately one softer than failure retries) → else bump failure_count, rewrite result to "Quality insufficient (score: N). Issues: ...", flip state FAILED, run the SAME strategy-validation ladder as hard failures (None→RETRY-or-first-enabled; recommended-not-enabled→first enabled with warning), preserve assignee, archive+cleanup, apply strategy. Missing assignee here logs "bug in the task assignment chain", marks FAILED, appends to completed, continues.
**Invariant:** Quality recovery REUSES the failure machinery end-to-end — only the limit differs (`max_retries-1` floor 1). Porters who reuse plain `max_retries` silently change the acceptance policy.
**Probe:** `grep -c 'quality_retry_limit' camel/societies/workforce/workforce.py` → 2.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-camel", query: "_analyze_task quality_sufficient quality_retry_limit recovery_strategy", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the shared-recovery-with-softer-limit pattern when adding post-hoc quality gates. Adapt scoring prompt. Omit the deprecated QualityEvaluation model (utils.py :139-166).
