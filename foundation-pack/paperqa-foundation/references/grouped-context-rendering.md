<!-- capsule-v2 -->
# Grouped context rendering — how do contexts from multiple questions render into one qa prompt?

**Source:** paper-qa Apache-2.0 `main@57e89f72`; Codebase Memory `paper-qa`. **Question:** When a session carries contexts gathered for several sub-questions, how are they grouped and ordered in the serialized context block?

## Connected graph-selected seam
**Path/Symbol:** `src/paperqa/settings.py:Settings.context_serializer` (:1202-1273), grouping branch gated by `answer.group_contexts_by_question`.
**Signature:** `async def context_serializer(self, contexts: Sequence[Context], question: str, pre_str: str | None) -> str`.
**Data Shape:** Input contexts may carry an optional `question` tag (set by GatherEvidence's question swap) or none (externally supplied). Sort-cap-filter runs FIRST (`(-score, name)` sort, `answer_max_sources` cap, `evidence_relevance_score_cutoff` filter — owned by `context-serializer-cannot-answer`); grouping happens only on the survivors.

### Decisive source
```python
if answer_config.group_contexts_by_question:
    contexts_by_question: dict[str, list[Context]] = defaultdict(list)
    for c in filtered_contexts:
        # Fallback to the main session question if not available.
        context_question = getattr(c, "question", question)
        contexts_by_question[context_question].append(c)
    context_sections = []
    for context_question, contexts_in_group in contexts_by_question.items():
        inner_strs = [context_inner_prompt.format(
            name=c.id, text=c.context, citation=c.text.doc.formatted_citation,
            **(c.model_extra or {})) for c in contexts_in_group]
        section = f'Contexts related to the question: "{context_question}"\n\n' + "\n\n".join(inner_strs)
        context_sections.append(section)
    context_str_body = "\n\n---\n\n".join(context_sections)
...
return prompt_config.context_outer.format(
    context_str=context_str_body,
    valid_keys=", ".join([c.id for c in filtered_contexts]))
```

**Flow:** sort→cap→filter (unchanged from flat mode) → group survivors by their question tag in FIRST-APPEARANCE order (defaultdict insertion order; untagged contexts fall back to the session question) → render each group under a quoted-question heading → join groups with `\n\n---\n\n` → the outer template's `valid_keys` still spans ALL groups, so citation-key validity is group-agnostic.
**Invariant:** Grouping never reorders across relevance ranks within a group or promotes a low-scored group ahead of a high-scored one at group level — group order is first-appearance of the already-sorted list, so the strongest evidence's question leads. The `getattr(c, "question", question)` fallback keeps externally-constructed sessions rendering instead of crashing.
**Probe:** `tests/test_paperqa.py::test_aquery_groups_contexts_by_question` (:1043-1114) pins both headings present, the `\n\n---\n\n` separator, and positional ordering `q1_header < context1 < q2_header < context3` (first question's header renders first). Deterministic source/test-range probe (no runner provisioned).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "paper-qa", query: "context_serializer group_contexts_by_question valid_keys", limit: 10 });
```

## Verdict
Adopt group-after-filter ordering with per-question headers when serving multi-sub-question agent sessions; adapt heading wording to your prompt schema but keep `valid_keys` global so the bibliography sweep stays single-pass; omit grouping entirely for single-question sessions (flag defaults off). Coverage: settings.py no_recorded_issue + metadata_match @ gen 2026-08-25T19:57:59Z.
