<!-- capsule-v2 -->
# Community-report attach + Go twin parity — how do top-ranked entities pull in their community summaries, identically on both sides of the stack?

**Source:** ragflow Apache-2.0 `main@9ea83b7a9d003d948fe4c99c6f35de02115a96e8`; Codebase Memory `ragflow`. **Question:** What is the exact query contract for community reports, and what must a second-language port preserve to stay behavior-identical?

## Membership filter + weight order, twice
**Path/Symbol:** Python `rag/graphrag/search.py:277-295` (`KGSearch._community_retrieval_`); Go twin `internal/service/graph/search.go:77-84` (`SearchCommunityReports`), `:186-202` (`buildCommunitySearchRequest`), `:271-287` (`ParseCommunityReportChunks`).
**Signature:** Python `def _community_retrieval_(self, entities, condition, kb_ids, idxnms, topn, max_token)`; Go `func SearchCommunityReports(ctx, docEngine engine.DocEngine, kbIDs []string, entityNames []string, topN int) ([]KGCommunityReport, error)`.
**Data Shape:** Community reports are doc-store chunks with `knowledge_graph_kwd="community_report"`, `entities_kwd` (member entity names), `weight_flt`, and JSON `content_with_weight` = `{report, evidences, ...}` (the pass-2 community-report-recovery schema).

### Decisive source
```python
# search.py:279-291
odr.desc("weight_flt")
fltr["knowledge_graph_kwd"] = "community_report"
fltr["entities_kwd"] = entities              # membership: any report containing a top entity
comm_res = self.dataStore.search(fields, [], fltr, [], odr, 0, topn, idxnms, kb_ids)
...
txts.append("# {}. {}\n## Content\n{}\n## Evidences\n{}\n".format(
    ii + 1, row["docnm_kwd"], obj["report"], obj["evidences"]))
max_token -= num_tokens_from_string(str(txts[-1]))
```
```go
// search.go:186-202 — byte-for-byte mirror of the same contract
req := &types.SearchRequest{
    SelectFields: []string{"docnm_kwd", "content_with_weight", "weight_flt", "entities_kwd"},
    Filter:       map[string]interface{}{"knowledge_graph_kwd": "community_report"},
    OrderBy:      (&types.OrderByExpr{}).Desc("weight_flt"),
}
if len(entityNames) > 0 { req.Filter["entities_kwd"] = filters }
// search.go:276-277 — drop rule: empty title AND empty content ⇒ skip
if title == "" && content == "" { continue }
```

**Flow:** only the top-ranked entities from the fusion pass seed the filter → reports ordered by community weight desc, capped at `topn` (default `comm_topn=1`) → each rendered as markdown with title/report/evidences, paying its token cost against the budget left over from entities+relations → appended as the third section of the single KG pseudo-chunk. The Go service exposes the identical query for the Go-side engine path; both sides share the field names so one index serves either consumer.
**Invariant:** Report selection is *membership-driven* (`entities_kwd` intersection with query-relevant entities), never text-similarity-driven; ordering is always `weight_flt` desc so the heaviest community wins the default top-1 slot; an empty entity list still searches (unfiltered except kind) in Go — but Python callers only invoke it with non-empty entity lists.
**Probe:** ACTIVE direct tests in `internal/service/graph/search_test.go`: `TestBuildCommunitySearchRequest_Basic/EmptyNames` (filter present iff names non-empty, OrderBy set), `TestParseCommunityReportChunks_Basic/EmptyTitle/NilInput` (weight decode, drop-on-both-empty, nil-safe). Python side has no dedicated test (source-read caveat).

## Get live surrounding code
**Retrieve:** (executed this pass)
```ts
await mcp.codebase_memory.search_graph({ project: "ragflow", query: "graphrag query retrieval entities keywords community report", filePattern: "*search*" });
// rank-2 = internal/service/graph.ParseCommunityReportChunks :271-287;
// rank-11 = SearchCommunityReports :77-84; rank-16 = buildCommunitySearchRequest :186-202
```
Direct full reads: `internal/service/graph/search.go` (:60-306) and `internal/service/graph/search_test.go` (447 lines, all active).

## Verdict
Adopt the membership-filter + weight-desc-order + top-1-default attach pattern and the shared index-field contract that lets two language stacks serve one store. Adapt the markdown rendering and budget accounting to your prompt format; omit the Go twin if single-stack. The Go builders also demonstrate the graceful-degradation ladder worth copying: dense expr nil ⇒ text-only match exprs; question empty ⇒ no match exprs at all.
