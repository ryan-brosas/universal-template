<!-- capsule-v2 -->
# Goal/plan prompt assembly — how do goal fields become planner prompts without letting an empty list fabricate content?

**Source:** pipeshub-ai Apache-2.0 `main@c28d133…`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-pipeshub-ai`. **Question:** What is the exact rendering contract that turns Goal(description, requirements, success_criteria) into a planning prompt — and where do empty-list and truncation edge cases live?

## Three-section template with per-line bullets; empty lists render as empty sections, never invented defaults
**Path/Symbol:** `backend/python/app/agent_loop_lib/modules/pipeline/planner/default.py:DefaultPlanner.plan` (:27–40) + `planner/base.py:Plan/Planner/extract_trailing_confidence` + `core/context.py:RunContext.child` (identity threading for sub-agent planners).
**Signature:** user_text built as f-string over `goal.description`, `chr(10).join(f"- {r}" for r in goal.requirements)`, same for `success_criteria`; response text stored VERBATIM on `Plan(goal, text, confidence=extract_trailing_confidence(text))`.
**Data Shape:** Prompt = fixed decomposition instruction + `Goal:` line + `Requirements:` bullet block + `Success criteria:` bullet block. Output = raw model text (never post-processed beyond confidence extraction); plan phases follow the system-prompt grammar `1. Phase Name: description`.

### Decisive source
```python
user_text = (
    f"Decompose this goal into execution phases:\n\n"
    f"Goal: {goal.description}\n\n"
    f"Requirements:\n{chr(10).join(f'- {r}' for r in goal.requirements)}\n\n"
    f"Success criteria:\n{chr(10).join(f'- {s}' for s in goal.success_criteria)}"
)
response = await self._model.complete(messages=[user_msg], system=_SYSTEM_PROMPT)
text = response.message.text
return Plan(goal=goal, text=text, confidence=extract_trailing_confidence(text))
```

**Flow:** Goal → three-section user message (system prompt carries the numbered-phase + trailing-Confidence-line format contract) → `complete()` → text verbatim into Plan → downstream consumers parse phases/confidence off the text (structured-plan-slot's legacy path streams this same text including its trailing Confidence line).
**Invariant:** (1) The plan is the RAW TEXT — no server-side phase parsing means the model's own formatting survives round-trips to UIs and eval harnesses; parsing lives only at confidence extraction. (2) Empty requirements/criteria render as EMPTY sections (join of nothing) rather than placeholder text — inventing defaults here fabricates constraints the executor will be graded against. (3) The trailing `Confidence:` line must stay LAST (system prompt forbids anything after it) because `extract_trailing_confidence` reads the final line.
**Probe:** `backend/python/tests/unit/agent_loop_lib/modules/pipeline/planner/test_default.py::test_prompt_includes_goal_requirements_and_success_criteria` (:40) + `::test_returns_raw_text_verbatim` (:34) + `::test_odd_format_response_never_raises` (:50).
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph '{"project":"mnt-hdd-utopia-inspo-platforms-pipeshub-ai","query":"DefaultPlanner plan goal requirements success_criteria extract_trailing_confidence","detail":"ids","limit":5}'
```

## Verdict
Adopt verbatim-text plans with confidence-as-trailing-line and empty-section honesty. Adapt section labels/format grammar to host prompts. Omit nothing. Covered by direct tests.
