<!-- capsule-v2 -->
# JSON rescue grammars — which extraction ladders recover structure from malformed LLM output, and why must the agent regex be GREEDY?

**Source:** gpt-researcher Apache-2.0 `main@5d84d2f5553e70a2765a8ff3a0d2672d60437ce8`; Codebase Memory `gpt-researcher`. **Question:** How do agent selection and deep research parse JSON that arrives wrapped in prose, fences, or line-grammar form?

## Two complementary rescue stacks
**Path/Symbol:** `gpt_researcher/actions/agent_creator.py:65-131` (`handle_json_error`, `extract_json_with_regex`); `gpt_researcher/skills/deep_research.py:20-59` (`JSON_BLOCK_PATTERNS`), `:62-205` (line-grammar parsers QUERY/GOAL/QUESTION/LEARNING).
**Signature:** `def extract_json_with_regex(response: str | None) -> str | None`; `def _extract_json_payloads(response: str) -> list[str]`.
**Data Shape:** Deep-research pattern order: fenced ```json blocks → `[...]` → `{...}`; deduped candidate list. Line grammars accept optional bullets/numbering and are case-insensitive; LEARNING carries `[citation]` bracket group with URL fallback extracted from the learning text itself.

### Decisive source
```python
# Greedy ``{.*}`` so the match spans from the first ``{`` to the LAST ``}``
# in the response... A non-greedy ``{.*?}`` stopped at the first ``}``,
# truncating any object with more than one key or with a ``}`` inside a
# string value (e.g. an agent_role_prompt mentioning "{markets}") into invalid JSON.
json_match = re.search(r"{.*}", response, re.DOTALL)
```

**Flow:** try strict `json.loads` → `json_repair.loads` → greedy regex object extraction → for deep research additionally the line-grammar state machine (query/goal pairs accumulate across lines) → final fallback returns "Default Agent" persona or empty results.
**Invariant:** greediness is CORRECT here despite the usual advice — every key of the object matters more than match minimality; the comment documents the historical non-greedy bug. json_repair output shape varies (list/dict/string/None), hence `_normalize_sub_queries` downstream.
**Probe:** `tests/test_extract_json_with_regex.py` pins multi-key survival + brace-inside-string + None/no-JSON; battery P14a/B8/B9 GREEN executing the lifted function.
