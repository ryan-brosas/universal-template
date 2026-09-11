<!-- capsule-v2 -->
# Result-insufficiency veto — How do you catch a worker that claims DONE but returned garbage or a refusal?

**Source:** CAMEL-AI/camel Apache-2.0 `master@13dc7a7d`; Codebase Memory `ext-camel`. **Question:** What textual heuristics flip a self-reported successful task into FAILED before the supervisor trusts it?

## Layered content validator + wrapper
**Path/Symbol:** `camel/tasks/task.py:validate_task_content` (:59-145), `is_task_result_insufficient` (:148-168).
**Signature:** `validate_task_content(content, task_id="unknown", min_length=1, mode=TaskValidationMode.INPUT, check_failure_patterns=True) -> bool`; `is_task_result_insufficient(task) -> bool`.
**Data Shape:** INPUT mode = structural only; OUTPUT mode adds refusal-pattern scanning over `content_lower`.

### Decisive source
```python
failure_indicators = ["i cannot complete", "i cannot do", "task failed",
    "unable to complete", "cannot be completed", "failed to complete",
    "i cannot", "not possible", "impossible to", "cannot perform"]
if any(indicator in content_lower for indicator in failure_indicators):
    return False
if content_lower.startswith(("error", "failed", "cannot", "unable")):
    return False
```

**Flow:** None → reject → strip-whitespace-empty → reject → shorter than `min_length` → reject → OUTPUT-only: substring scan of the ten failure indicators, then startswith check on four prefixes → pass. `is_task_result_insufficient` treats missing attribute/None result as insufficient and wraps the validator with `mode=OUTPUT, check_failure_patterns=True`. Consumers enforce it in TWO places: `SingleAgentWorker._process_task` returns FAILED right after the LLM's own TaskResult.failed flag (:577-582), and the supervisor's `_listen_to_channel` re-vetoes on the returned task (`is_task_result_insufficient(returned_task)` :5432) rewriting state FAILED so it flows through the recovery ladder with log "marked as DONE but result is insufficient".
**Invariant:** The validator is deliberately case-insensitive substring matching, not regex anchoring — porters who "tighten" it to word boundaries break detection of padded refusals; porters who drop the startswith rung let "Error: ..." results pass.
**Probe:** `python3 - <<'EOF'
import re
src = open('camel/tasks/task.py').read()
inds = ["i cannot complete", "i cannot do", "task failed", "unable to complete", "cannot be completed", "failed to complete", "i cannot", "not possible", "impossible to", "cannot perform"]
print(len(inds), all(i in src for i in inds))
EOF` → `10 True`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-camel", query: "validate_task_content failure_indicators is_task_result_insufficient", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-rung heuristic (indicator substrings + prefix) as a cheap pre-LLM quality gate at both worker and supervisor layers. Adapt indicator vocabulary per language/domain. Omit `TaskValidationMode.INPUT` uses if you have no decomposition-input gate.
