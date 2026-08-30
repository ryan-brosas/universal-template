<!-- capsule-v2 -->
# Context serialization & cannot-answer sentinel — how do top-scored contexts become one prompt block with valid keys, and when does the pipeline refuse to answer?

**Source:** paper-qa (Apache-2.0) `main@57e89f72`; Codebase Memory `ext-paper-qa`. **Question:** How are evidence contexts sorted/capped/formatted into the qa prompt, and what exact condition produces "I cannot answer" instead of an LLM call?

## Connected graph-selected seam
**Path/Symbol:** `src/paperqa/settings.py:Settings.context_serializer` (:1202-1273) + `src/paperqa/docs.py:aquery` (:643-654) + `src/paperqa/prompts.py` (`CONTEXT_OUTER_PROMPT` :164, `EMPTY_CONTEXTS = len(outer.format(context_str="", valid_keys="").strip())` :165, `CANNOT_ANSWER_PHRASE` :28).
**Signature:** `async def context_serializer(self, contexts: Sequence[Context], question: str, pre_str: str | None) -> str`.
**Data Shape:** Sort key `(-score, name)`; cap `answer_max_sources` (default 5); THEN filter `score >= evidence_relevance_score_cutoff` (default 1). Inner template requires `{name}` (=Context.id!) and `{text}`; outer appends `Valid Keys: pqac-a, pqac-b`.

### Decisive source
```python
filtered_contexts = sorted(contexts, key=lambda x: (-x.score, x.text.name))[:answer.answer_max_sources]
filtered_contexts = [c for c in filtered_contexts if c.score >= answer.evidence_relevance_score_cutoff]
...
if len(context_str.strip()) <= EMPTY_CONTEXTS:   # outer template rendered with empty body+keys
    answer_text = (f"{CANNOT_ANSWER_PHRASE} this question due to"
                   f" {'having no papers' if not self.docs else 'insufficient information.'}.")
```
Prompt contract (`prompts.qa_prompt`): cite via keys at sentence ends, only keys from context; `CITATION_KEY_CONSTRAINTS` enumerates valid vs invalid parenthetical forms INCLUDING banning "Author et al. (2023)" style.

**Flow:** optional `pre` LLM call injects question-specific prep (its output rides into context as "Extra background information:", strippable by `answer_filter_extra_background` regex) → serialize → EMPTY check happens BEFORE spending the big call → answer → example-citation scrub `(pqac-...)` literal removed if echoed → post hook REPLACES answer_text then CONCATENATES old (:708-711 quirk).
**Invariant:** CANNOT_ANSWER threshold is computed FROM the outer template length — change the template and the constant follows automatically; sorting happens before BOTH cap and cutoff, so cutoff can shrink below max_sources but never reorder.
**Probe:** `tests/test_paperqa.py::test_aquery_groups_contexts_by_question` (:1043), `::test_context_inner_outer_prompt` (:2676), `::test_custom_context_str_fn` (:1018); executed grep pins EMPTY_CONTEXTS derivation prompts.py:165.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "ext-paper-qa", query: "context_serializer CANNOT_ANSWER_PHRASE EMPTY_CONTEXTS", limit: 10 });
```
**Retrieve:** graph links serializer to PromptSettings validators (custom prompts must stay within base template's variable set — enforced by `get_formatted_variables` subset checks).

## Verdict
Adopt sort-cap-filter order + template-derived emptiness constant + refusal taxonomy; adapt wording of the sentinel (it doubles as a test fixture upstream); omit group-by-question rendering unless serving multi-question sessions. Coverage: cited paths no_recorded_issue.
