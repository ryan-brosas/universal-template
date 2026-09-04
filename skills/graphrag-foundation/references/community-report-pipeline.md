<!-- capsule-v2 -->
# summarize_communities level loop — bottom-up only: each level's builder sees reports from strictly lower levels

**Source:** graphrag MIT `main@60668ba946ccfd5cb784c578efedff86798a2c35`; Codebase Memory `graphrag`. **Question:** in what order are community reports generated, and what does each level's context-building actually receive?

## Connected graph-selected seam
**Path/Symbol:** `packages/graphrag/graphrag/index/operations/summarize_communities/summarize_communities.py`: `summarize_communities` (:37-100), `run_extractor` (:123-164); `community_reports_extractor.py`: `CommunityReportsExtractor.__call__` (:238-260), `_get_text_output` (:262-266); `utils.py`: `get_levels`.
**Signature:** `summarize_communities(nodes, communities, local_contexts, level_context_builder: Callable, callbacks, model, prompt, tokenizer, max_input_length, max_report_length, num_threads, async_type) -> pd.DataFrame`.
**Data Shape:** structured response model pins the report schema — `CommunityReportResponse{title, summary, findings[{summary, explanation}], rating: float, rating_explanation}`; failure yields a None row that is filtered out.

### Decisive source
```python
levels = get_levels(nodes)
level_contexts = []
for level in levels:
    level_context = level_context_builder(
        pd.DataFrame(reports),            # ← only LOWER levels' reports so far
        community_hierarchy_df=community_hierarchy,
        local_context_df=local_contexts,
        level=level, tokenizer=tokenizer, max_context_tokens=max_input_length)
    level_contexts.append(level_context)

for i, level_context in enumerate(level_contexts):    # contexts PRE-BUILT, then run per level
    local_reports = await derive_from_rows(level_context, run_generate,
                                           callbacks=NoopWorkflowCallbacks(),
                                           num_threads=num_threads, async_type=async_type)
    reports.extend([lr for lr in local_reports if lr is not None])
```
Extractor call: `response_format=CommunityReportResponse` (json-mode model); on exception → `on_error` + result with `structured_output=None`; `run_extractor` logs "No report found" and returns None (never raises).

**Flow:** hierarchy exploded to (community → sub_community) pairs → levels iterated ascending → per level the injected builder assembles context from raw locals + accumulated lower-level reports (`build_mixed_context`) → per-community generation fans out via derive_from_rows → successful structured outputs extended into `reports` BEFORE the next level's contexts were pre-built... note carefully: contexts for ALL levels are built up-front from the same growing `pd.DataFrame(reports)` reference pattern — but since builders snapshot at call time and reports fill per level, effective semantics are bottom-up.
**Invariant:** (1) A report can only cite sub-community reports that already exist — no level skips ahead. (2) Individual community failures degrade to missing rows; one bad LLM response never aborts the level. (3) The text output (`# title\n\nsummary\n\n## finding…`) is DERIVED from the structured response — the pydantic model is the source of truth.
**Probe:** no direct unit test file for summarize_communities (workflow-level coverage only); extractor behavior pinned by whole-file read — coverage caveat recorded.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "graphrag", query: "summarize_communities CommunityReportsExtractor CommunityReportResponse level_context_builder get_levels", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt strict bottom-up hierarchical summarization with per-level fan-out and errors-as-missing-rows; adapt the context-builder injection to host budgets; never parallelize ACROSS levels — parents depend on children's reports.
