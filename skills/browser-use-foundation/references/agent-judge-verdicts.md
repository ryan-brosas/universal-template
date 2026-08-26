<!-- capsule-v2 -->
# Agent judge verdicts — LLM-as-judge over an agent trace with ground-truth precedence and self-report separation

**Source:** browser-use MIT `main@85ddbfedf609`; Codebase Memory `browser-use`. **Question:** how do you score an agent run with a second LLM pass so the verdict is comparable across runs and never corrupts the agent's own success state?

## Connected graph-selected seam
**Path/Symbol:** `browser_use/agent/judge.py` (225 lines): `construct_judge_messages` (:44+), `_truncate_text` (:34-41), `_encode_image` (:21-31); wired at `agent/service.py` `_judge_trace` (:1587-1620) + `_judge_and_log` (:1622-1662); mirrored in `beta/service.py`.
**Signature:** `construct_judge_messages(task, final_result, agent_steps, screenshot_paths, max_images=10, ground_truth=None, use_vision=True|'auto') -> list[BaseMessage]`; `_judge_trace -> JudgementResult | None` via `judge_llm.ainvoke(messages, output_format=JudgementResult)`.
**Data Shape:** `JudgementResult{verdict: bool, failure_reason, reasoning, reached_captcha, impossible_task}` as structured output; screenshots enter as `ContentPartImageParam` data URLs (`data:image/png;base64,...`, media_type png); per-field text budget 40000 chars.

### Decisive source
```python
# uniform truncation budget per field; head/tail variants keep the eval marker inside the limit
if len(text) <= max_length:
    return text
if from_beginning:
    return '...[text truncated]' + text[-max_length + 23:]
return text[:max_length - 23] + '...[text truncated]...'

# only the LAST N screenshots (most recent page states win)
selected_screenshots = screenshot_paths[-max_images:] if len(screenshot_paths) > max_images else screenshot_paths

# ground truth is injected as an ABSOLUTE-priority section when present
"""**GROUND TRUTH VALIDATION (HIGHEST PRIORITY):**
...If the ground truth is not satisfied by the agent's execution and final response, the verdict MUST be false."""

# service wiring: structured output, provider-specific request typing, never-throws evaluation
kwargs = {'output_format': JudgementResult}
if self.judge_llm.provider == 'browser-use':
    kwargs['request_type'] = 'judge'; kwargs['session_id'] = self.session_id
try:
    response = await self.judge_llm.ainvoke(input_messages, **kwargs)
    return response.completion            # JudgementResult
except Exception as e:
    self.logger.error(f'Judge trace failed: {e}')
    return None                           # judge outage must not fail the run

# _judge_and_log: attach WITHOUT overriding the agent self-report
last_result.judgement = judgement         # ActionResult.judgement
# last_result.success stays the agent's own claim; telemetry compares both
```

**Flow:** run ends -> history yields final_result/agent_steps/screenshot_paths -> messages assembled (truncated fields, last-N images, criteria order: task satisfaction > output quality > tool effectiveness > reasoning > browser handling; explicit FAILURE CONDITIONS auto-false list; IMPOSSIBLE TASK DETECTION rules distinguishing vague/broken/auth-blocked from merely poor execution) -> judge LLM returns structured JudgementResult -> verdict attached to the last done ActionResult -> logging only when self-report and verdict DISAGREE (plus PASS/FAIL line otherwise suppressed on agreement) -> `reached_captcha` triggers a cloud-browser upsell nudge.
**Invariant:** judge failure returns None and logs — evaluation can never break or alter the run; the agent's `success` self-report is never mutated (dual-value comparison preserved for telemetry); missing image files degrade silently (`_encode_image` returns None and is skipped); vision off removes images entirely rather than sending empty parts.
**Probe:** from repo root, call `construct_judge_messages` with a tiny task/result/steps plus one real small PNG path and assert message count and image part presence; boundary-check `_truncate_text` at exactly max_length and max_length+1 (executed this pass; output in verification.md).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-use", query: "judge construct messages verdict ground truth impossible task", file_pattern: "browser_use/agent/*", limit: 12 });
```

## Verdict
Adopt for any agent-eval harness: fixed per-field char budgets, tail-biased screenshot selection, a written criteria ORDER plus an explicit auto-false list, separate impossible-task classification, structured output format, and strict dual-bookkeeping (self-report vs judge) so downstream analytics can measure honesty gaps. Adapt the prompt wording to your domain; keep the None-on-failure contract.
