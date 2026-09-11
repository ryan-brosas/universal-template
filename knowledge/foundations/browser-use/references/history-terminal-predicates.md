<!-- capsule-v2 -->
# History terminal predicates — last-result-wins reads and input-only serialization

**Source:** browser-use MIT `main@85ddbfedf609`; Codebase Memory `browser-use`. **Question:** how should an agent's history expose "did it finish / succeed / get judged" without scanning, and how should saved histories redact secrets?

## Connected graph-selected seam
**Path/Symbol:** `browser_use/agent/views.py`: `AgentHistoryList.errors` (:709-717), `final_result` (:719-725), `is_done` (:727-732), `is_successful` (:734-740, 17 in-edges), `judgement/is_judged/is_validated` (:746-767), `urls` (:769-771), `screenshot_paths` (:773-786); `AgentHistory.model_dump` (:550-589).
**Signature:** `is_done() -> bool`; `is_successful() -> bool | None` (None = not done yet); `final_result() -> str | None`; `model_dump(sensitive_data=None, **kwargs) -> dict`.
**Data Shape:** every terminal predicate reads ONLY `history[-1].result[-1]`; positional families (`errors`, `urls`, `screenshot_paths`) keep one slot per step with explicit `None` for absent values ("each step can have only one error").

### Decisive source
```python
# :734-740 — tri-state terminal answer; the agent decides IN THE LAST STEP
def is_successful(self) -> bool | None:
    if self.history and len(self.history[-1].result) > 0:
        last_result = self.history[-1].result[-1]
        if last_result.is_done is True:
            return last_result.success
    return None

# :577-578 — results are deliberately NEVER secret-filtered on dump...
# Handle result serialization - don't filter ActionResult data
# as it should contain meaningful information for the agent
result_dump = [r.model_dump(exclude_none=True, mode='json') for r in self.result]
```

**Flow:** steps append history items -> callers ask terminal questions and get O(1) last-result answers (no scanning back through steps) -> `model_dump` filters `sensitive_data` ONLY inside action `'input'` params (guard `if 'input' in action`) while result dumps stay unfiltered by design -> `load_from_dict` re-validates stored `model_output` against a CALLER-SUPPLIED output_model so histories saved under one action schema reload under another.
**Invariant:** last-result-wins everywhere: probe showed a two-step list (error step + done step) → `is_done True, is_successful True, final_result 'ok', errors ['boom', None], len(urls()) == 2, judgement verdict True, total_duration_seconds() == 1.0`. DOC-VS-CODE DRIFT: `urls()` docstring says "all unique URLs" but the implementation is positional per-step and keeps duplicates (:769-771) — code wins. Consumer pinning: tests/ci/test_rerun_ai_summary.py drives AgentHistoryList over constructed histories (:174-252 range read this pass); browser-launching execution stays environment-blocked (needs real Chrome) — cited source-read only.
**Probe:** `.venv/bin/python -c` from repo root: build two AgentHistory items (StepMetadata 0→1s; JudgementResult(verdict=True)) into AgentHistoryList; assert the seven-value tuple above (executed this pass; outputs in verification.md).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-use", query: "AgentHistoryList is_done is_successful final_result urls", limit: 10 });
```
Executed during discovery: rank-2 `is_done` :727-732.

## Verdict
Adopt last-result-wins terminal predicates plus positional-with-None step families — they make run summaries O(1) and honest about partial steps. Adopt input-only secret filtering for SAVED histories but pair it with sensitive-redaction-ladder, which owns the separate MESSAGE-path redaction (the executed test pins that path). Adapt which fields are "results" in your host. Coverage caveat: no dedicated views.py test file exists upstream.
