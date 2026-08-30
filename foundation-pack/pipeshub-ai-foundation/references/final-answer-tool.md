<!-- capsule-v2 -->
# final_answer (structured terminal tool + prompt-adjacent formatting rules)

## Source
pipeshub-ai Apache-2.0 `main@4a02110d`; Codebase Memory `pipeshub-ai`. **Question:** How do you deliver the agent's answer as a structured tool call without breaking streaming — and where should response-format rules live?

## Path/Symbol
`tools/builtin/planning/final_answer.py` — `_answer_markdown_description()` (:35–78), `_build_parameters()` lazy confidence fields (:81–143), `FinalAnswerTool.extract_outcome()` staticmethod (:194–237), `final_answer_enabled()` gate (:240–254).

## Signature
Tagged `TAG_LIFECYCLE_TERMINAL` so the existing loop tag-dispatch stops the run with NO edits to `Agent.step()`/ReActLoop (:4–6). Parameters built LAZILY per access (`parameters` property → `_build_parameters()`) so the `confidence`/`confidence_reason` pair appears only when `confidence_enabled()`.

## Data Shape
Args: `answer_markdown` (required), optional `sources_used[]` / `unavailable_sources[]` (UI display), conditional `confidence` enum + one-sentence reason. `extract_outcome(tr, call, fallback_text)` mirrors TaskCompleteTool's ladder: dict content → `answer_markdown`, else `str(c)`; empty after fallback ⇒ error_result bounce; confidence normalized via `app.agents.agent_loop.confidence.normalize` then mapped to the SAME three-level Confidence enum task_complete uses (:218–228).

### Decisive source
```python
def final_answer_enabled() -> bool:
    """...Defaults to **False**.  The final_answer tool wraps the entire answer in
    a JSON tool-call payload, which breaks streaming for small models and
    adds complexity ... for marginal benefit. The text-based
    approach — model writes plain text, confidence parsed from a trailing
    marker — is more reliable across all model tiers.
    Set to 'true' only for frontier-model deployments..."""
    from app.agents.agent_loop.env_utils import env_bool
    return env_bool("PIPESHUB_ENABLE_FINAL_ANSWER", False)
```

**Flow:** model calls final_answer once when done → loop stops via tag → extract_outcome lifts markdown/confidence → UI gets sources_used/unavailable_sources for coverage warnings. Formatting/citation rules (tables at 3+ items, `[source](refN)` citation grammar, record/block structure) live in the PARAMETER DESCRIPTION, not the always-on system prompt — instruction proximity: rules appear exactly when the model writes the answer, shrinking the base prompt (:7–11).

**Invariant:** SOURCE WINS over this file's own stale module docstring: the flag defaults FALSE (`env_bool(..., False)`), docstring lines :18–21 claiming "default True" are outdated. Default-off exists because a JSON-wrapped terminal answer breaks small-model streaming; enable only for frontier deployments. Citation IDs are opaque tokens replaced by the system downstream — never real URLs.

**Probe:** No dedicated FinalAnswerTool unit test (coverage caveat): extract_outcome contract is exercised indirectly via adapter tests (test_prompt_builder.py, evals/test_golden_assertions.py reference final_answer behavior); the shared extract_outcome semantics are pinned by test_task_complete.py.

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph --project pipeshub-ai --semantic-query '["FinalAnswerTool","final_answer_enabled","answer_markdown"]'
```

## Verdict
Adopt parameter-description-as-rule-home (instruction proximity) and the same-enum-as-task_complete confidence reuse; adopt the DEFAULT-OFF verdict on structured terminal output for small models (plain-text + trailing marker is the portable default); adapt citation grammar to host's retrieval format.
