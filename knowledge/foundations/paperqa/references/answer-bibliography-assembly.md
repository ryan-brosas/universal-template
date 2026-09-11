<!-- capsule-v2 -->
# Answer→bibliography assembly — how do pqac keys in the raw answer become a formatted answer plus a numbered references section?

**Source:** paper-qa (Apache-2.0) `main@57e89f72`; Codebase Memory `ext-paper-qa`. **Question:** How are parenthetical citation keys converted to docname citations, hallucinated keys erased, and the bibliography ordered — without trusting the LLM's own reference list?

## Connected graph-selected seam
**Path/Symbol:** `src/paperqa/types.py:PQASession.populate_formatted_answers_and_bib_from_raw_answer` (:474-526) + `utils.get_parenthetical_substrings` (:170-188) + `utils.get_citation_ids` (:191-194); invoked as the LAST step of `docs.aquery` (:719).
**Signature:** `def populate_formatted_answers_and_bib_from_raw_answer(self) -> None` (mutates session: `.answer`, `.formatted_answer`, `.references`).
**Data Shape:** Maps built from contexts only: `id_to_name = {c.id: c.text.name}`, `name_to_citation = {c.text.name: c.text.doc.formatted_citation}`. Parentheticals containing ≥1 known id get rewritten to `(", ".join(deduped_names))`; bib entries numbered by FIRST-MENTION order (`dict.fromkeys` dedupe).

### Decisive source
```python
for parenthetical in get_parenthetical_substrings(formatted_without_references):
    deduped_names = dict.fromkeys(id_to_name_map[key] for key in get_citation_ids(parenthetical)
                                  if id_to_name_map.get(key))
    if deduped_names:
        formatted_without_references = formatted_without_references.replace(
            parenthetical, f"({', '.join(deduped_names)})")
        ...  # name_bib[deduped_name] = citation (first mention wins)
# strip out any leftover hallucinated citations
included_keys = get_citation_ids(self.raw_answer)
for hallucinated_key in set(included_keys) - set(id_to_name_map):
    formatted_without_references = formatted_without_references.replace(hallucinated_key, "")
bib = "\n\n".join(f"{i+1}. ({k}): {c}" for i, (k, c) in enumerate(name_bib.items()))
```

**Flow:** Nested-parenthesis-safe extraction (stack of open indices) → id scan per parenthetical → rewrite-or-leave → hallucination sweep deletes unknown `pqac-*` tokens entirely → assemble `Question:` header + References section. `used_contexts` computed field cross-checks which ids actually appear in `raw_answer`.
**Invariant:** The bibliography is derived ONLY from ids that resolve to gathered contexts — an LLM-invented citation can never reach References because its id fails `id_to_name_map`. First-mention order, not alphabetical.
**Probe:** `tests/test_paperqa.py::test_pqa_context_id_parsing` (:3475) + executed lifted probes T5a/T5b GREEN; aquery integration pinned by `test_json_evidence` (:875) and `test_nonduplicate_contexts` (:844).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-paper-qa", query: "populate_formatted_answers_and_bib get_citation_ids name_bib", limit: 10 });
```

## Verdict
Adopt resolve-then-sweep assembly for any keyed-citation RAG surface; adapt the id regex if your prefix differs; omit the Question-header formatting freely. Probes executed GREEN on lifted pure functions.
