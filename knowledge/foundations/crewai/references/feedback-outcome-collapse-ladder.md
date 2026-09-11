<!-- capsule-v2 -->
# Feedback outcome collapse ladder — how does free-form human feedback become one exact routing label without ever dead-ending the flow?

**Source:** crewAI MIT `main@9e9a8577becc322f98a966ad88d7904251049744`; Codebase Memory `ext-crewAI`. **Question:** What fallback order maps arbitrary text to a declared outcome, and what happens when everything fails?

## Structured output → JSON parse → case-insensitive → substring-longest → first
**Path/Symbol:** `lib/crewai/src/crewai/flow/runtime/__init__.py` (`Flow._collapse_to_outcome` :3739–3857; empty-feedback pre-gate `_finalize_human_feedback` :3606–3650).
**Signature:** `_collapse_to_outcome(self, feedback: str, outcomes: Sequence[str], llm: str | BaseLLM) -> str`.
**Data Shape:** builds per-call `class FeedbackOutcome(BaseModel): outcome: Literal[outcomes_tuple]` — a literal-typed pydantic model constructed AT RUNTIME from the outcome tuple.

### Decisive source
```python
if isinstance(response, str):
    try:
        parsed = json.loads(response)
        return str(parsed.get("outcome", outcomes[0]))
    except json.JSONDecodeError:
        response_clean = response.strip()
        for outcome in outcomes:
            if outcome.lower() == response_clean.lower():
                return outcome
        return outcomes[0]
...
# Partial match (longest wins, first on length ties)
best_len = -1
for outcome in outcomes:
    if outcome.lower() in response_lower and len(outcome) > best_len:
        best_outcome = outcome; best_len = len(outcome)
```

**Flow:** blank feedback never reaches the LLM (`_finalize_human_feedback`: default_outcome else emit[0]) → structured call with response_model returns a JSON STRING (in-source NOTE), not a model → parse ladder: json.loads → bare-string case-insensitive equality → substring containment with LONGEST-wins and first-on-tie → total failure of both calls still returns `outcomes[0]`. The result is recorded in `human_feedback_history` and `last_human_feedback` regardless.
**Invariant:** The collapse is TOTAL — every path returns a member of `outcomes`, so listener routing can never receive an unroutable label. Longest-substring preference matters: `"approve"` must win over `"approved with changes"` style overlaps in reverse. The runtime Literal construction is what makes providers honor the closed set via function-calling schemas.
**Probe:** `.venv/bin/python -m pytest "lib/crewai/tests/test_flow.py::test_router_with_multiple_conditions" -q` (expect 1 passed; pins label-driven routing); static anchor: `grep -c "best_len = -1" lib/crewai/src/crewai/flow/runtime/__init__.py` → 1 at :3838.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-crewAI", query: "_collapse_to_outcome structured FeedbackOutcome literal fallback prompting", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the five-rung total-collapse ladder and runtime-Literal schema; adapt rung order only if your LLM guarantees typed objects; omit history recording if you have no audit need. Coverage caveat: collapse internals have no dedicated upstream test — pinned indirectly through routing tests plus source inspection.
