<!-- capsule-v2 -->
# Grounded ask-a-question module contract — one reusable "search then answer with citations" unit for any conversational turn

**Source:** storm MIT `main@fb951af7`; Codebase Memory `storm`. **Question:** What is the full lifecycle of a grounded Q&A call — from question to query decomposition to cited answer — including what happens when retrieval returns nothing?

## AnswerQuestionModule end-to-end contract
**Path/Symbol:** `knowledge_storm/collaborative_storm/modules/grounded_question_answering.py:AnswerQuestionModule` (:50-163); helpers `format_search_results`, `extract_cited_storm_info` (`collaborative_storm_utils.py`:36-105).
**Signature:** `forward(topic: str, question: str, mode: str = "brief", style: str = "conversational", callback_handler=None) -> Prediction(question, queries, raw_retrieved_info, cited_info, response)`.
**Data Shape:** `cited_info: Dict[int, Information]` keyed by the LOCAL citation indices used inside this answer; `queries` is the capped, deduped query list actually sent to the retriever.

### Decisive source
```python
answer = "Sorry, there is insufficient information to answer the question."
if info_text:
    ...
    answer = ArticleTextProcessing.remove_uncompleted_sentences_with_citations(answer)
    answer = trim_output_after_hint(answer, hint="Now give your response. (Try to use as many different sources as possible and do not hallucinate.)")
    answer = separate_citations(answer)          # [1, 2] -> [1][2]
...
cited_searched_results = extract_cited_storm_info(response=answer,
                                                  index_to_storm_info=index_to_information_mapping)
```

**Flow:** (1) `QuestionToQuery` decomposes the question into a bullet list of search-box queries; lines are stripped of `-`/quotes and capped at `max_search_queries`; `set()` dedups before `retriever.retrieve(list(set(queries)), exclude_urls=[])`. (2) Every retrieved Information gets `meta["question"] = question` so later mind-map placement can group by intent. (3) `format_search_results(mode=...)` renders `"[n]: snippet"` text under a 1000-word budget (brief = first snippet per result; extensive = fill across snippets) AND returns the `index→Information` map. (4) Empty info_text keeps the canned refusal string; otherwise the answer ladder runs truncation → hint-trim → bracket-split. (5) Citation indices are resolved BACK to Information objects via regex `\[(\d+)\]` extraction against the map.
**Invariant:** (1) The canned default is assigned BEFORE generation and only replaced when `info_text` is non-empty — a refused answer still flows through `extract_cited_storm_info` harmlessly because it cites nothing. (2) The hint passed to `trim_output_after_hint` must equal the OutputField prefix byte-for-byte or the echo survives into user-visible text. (3) Citation indices are CALL-LOCAL; global identity is established only when `KnowledgeBase.update_from_conv_turn` rebinds them (see two-phase-citation-renumbering capsule). (4) `format_search_results` aborts on word-budget overflow mid-pair but keeps already-queued snippets — partial context is preferred over none.
**Probe:** byte-pins executed this pass — :129 canned default placement before the `if info_text:` block, :74-78 strip/cap/dedup chain, :89 meta tagging, :146 exact hint string, :149 separate_citations call, :82 `assert -1 not in index_mapping` in format_search_results. All line-exact.
**Coverage caveat:** both files checked `no_recorded_issue` @ gen 2026-08-25T20:09:07Z.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "storm", query: "AnswerQuestionModule QuestionToQuery retrieve_information format_search_results insufficient information", limit: 10 });
```

## Verdict
Adopt this module boundary verbatim for any chat turn that must cite live evidence (decompose → retrieve → tag-meta → budget-format → refuse-by-default → sanitize → rebind); adapt query caps and budgets; omit nothing in the ordering of the answer-sanitization ladder — running citation separation before sentence truncation, or trimming after rebinding, corrupts index mapping.
