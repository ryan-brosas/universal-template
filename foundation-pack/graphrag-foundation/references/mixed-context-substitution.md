<!-- capsule-v2 -->
# build_mixed_context substitution loop — replace biggest sub-community local contexts with their reports one at a time until the parent context fits

**Source:** graphrag MIT `main@60668ba946ccfd5cb784c578efedff86798a2c35`; Codebase Memory `graphrag`. **Question:** when a parent community's raw context exceeds the token budget, how does the pipeline trade local detail for sub-community reports to squeeze under the limit?

## Connected graph-selected seam
**Path/Symbol:** `packages/graphrag/graphrag/index/operations/summarize_communities/build_mixed_context.py`: `build_mixed_context` (:15-74); `graph_context/sort_context.py`: `sort_context` (:11-126), `parallel_sort_context_batch` (:129-164).
**Signature:** `build_mixed_context(context: list[dict], tokenizer: Tokenizer, max_context_tokens: int) -> str`.
**Data Shape:** input rows carry `all_context` (local entity/edge/claim dicts), `context_size`, `full_content` (sub-community report text, may be falsy), `sub_community`; output is ONE CSV-flavored context string.

### Decisive source
```python
sorted_context = sorted(context, key=lambda x: x[CONTEXT_SIZE], reverse=True)  # biggest first
for idx, sub in enumerate(sorted_context):
    if exceeded_limit:
        if sub[FULL_CONTENT]:
            substitute_reports.append({COMMUNITY_ID: sub[SUB_COMMUNITY], FULL_CONTENT: sub[FULL_CONTENT]})
        else:
            final_local_contexts.extend(sub[ALL_CONTEXT]); continue  # no report → keep raw
        remaining = [r for r in sorted_context[idx+1:]]               # rest stay RAW local
        new_string = sort_context(remaining_local + final_local_contexts,
                                  tokenizer, substitute_reports)
        if tokenizer.num_tokens(new_string) <= max_context_tokens:
            exceeded_limit = False; context_string = new_string; break
# ALL reports still over budget → greedy CSV of reports until full:
for sub in sorted_context:
    substitute_reports.append(...); new_string = pd.DataFrame(substitute_reports).to_csv(index=False)
    if num_tokens(new_string) > max_context_tokens: break
    context_string = new_string
```
`sort_context` itself: edges pre-sorted by `(-combined_degree, short_id)` then added one-by-one (dedup via id-sets), re-serializing the WHOLE csv each addition and stopping BEFORE the first over-budget serialization — degree-ranked entities/edges enter first.

**Flow:** rank sub-communities big→small → walk down, swapping each reported sub-community's raw context for its report and re-measuring after EVERY swap → stop at first fit; unreported subs always contribute raw context → fallback ladder packs reports greedily into a plain CSV when even all-report context can't fit.
**Invariant:** (1) Substitution is ordered by descending size — the largest consumers get compressed first. (2) A sub-community WITHOUT a report can never be substituted (its locals must ride along). (3) The final string is always measured, never assumed. (4) sort_context emits nothing that wasn't dedup'd by id — repeated endpoints across edges appear once.
**Probe:** no direct unit test for build_mixed_context/sort_context (community-report coverage lives at workflow level); pinned by whole-file source read — coverage caveat recorded.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "graphrag", query: "build_mixed_context sort_context substitute_reports exceeded_limit parallel_sort_context_batch", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt size-descending report-for-context substitution with per-swap remeasurement as the general "compress structured context into budget" recipe; adapt report format (CSV vs JSON) to host prompts; keep the no-report-must-stay-raw rule — dropping it fabricates content the pipeline doesn't have.
