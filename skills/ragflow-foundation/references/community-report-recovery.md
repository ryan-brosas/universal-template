<!-- capsule-v2 -->
# Community report extraction recovery — how do you checkpoint per-community LLM reports and survive malformed JSON without poisoning the graph?

**Source:** ragflow Apache-2.0 `main@9ea83b7a9d003d948fe4c99c6f35de02115a96e8`; Codebase Memory `ragflow`. **Question:** What is the per-community checkpoint key, the JSON repair ladder, and the schema gate that decides whether an LLM report is accepted?

## Membership-keyed replay + brace repair + typed schema gate
**Path/Symbol:** `rag/graphrag/general/community_reports_extractor.py:CommunityReportsExtractor.__call__` (:58-190), `_get_text_output` (:192-208); key builder `rag/graphrag/checkpoints.py:community_checkpoint_key` (:39-40).
**Signature:** `async def __call__(self, graph, callback=None, task_id="", checkpoints: dict | None = None, save_checkpoint=None)`.
**Data Shape:** Checkpoint payload: `{"structured_output": {title:str, summary:str, findings:list, rating:float, rating_explanation:str, weight, entities}, "output": str}`; key = sha256 over `(level, community_id, sorted(nodes))`.

### Decisive source
```python
if len(ents) < 2:
    return                                    # singleton communities skipped
checkpoint_key = community_checkpoint_key(str(level), str(cm_id), list(ents))
checkpoint = checkpoints.get(checkpoint_key)
if isinstance(checkpoint, dict):
    response = checkpoint.get("structured_output"); output = checkpoint.get("output")
    if isinstance(response, dict) and isinstance(output, str):
        add_community_info2graph(graph, response.get("entities", ents), response.get("title", ""))
        return                                # replayed, no LLM call

# LLM JSON repair ladder:
response = re.sub(r"^[^\{]*", "", response)   # strip junk before first {
response = re.sub(r"[^\}]*$", "", response)   # strip junk after last }
response = re.sub(r"\{\{", "{", response)     # un-escape doubled braces
response = re.sub(r"\}\}", "}", response)
response = json.loads(response)
if not dict_has_keys_with_types(response,
        [("title", str), ("summary", str), ("findings", list),
         ("rating", float), ("rating_explanation", str)]):
    return                                    # schema violation ⇒ report dropped, no crash
...
if save_checkpoint:
    await save_checkpoint(checkpoint_key, {"structured_output": response, "output": output})
```

**Flow:** node `"rank"` set from degree → leiden partitions (see leiden capsule) → one task per community under the shared chat limiter → replay-or-extract → accepted reports attach their title to member nodes (`communities` attr, deduped) and accumulate into `res_dict`/`res_str`; timeouts/parse failures skip that community only.
**Invariant:** The checkpoint key embeds SORTED membership — a composition change produces a new key and forces re-extraction (never serves a stale report for a changed community); replay validates shape before trusting it; a failed community degrades to "missing report", never aborts the run.

## Get live surrounding code
**Retrieve:** (executed this pass)
```ts
await mcp.codebase_memory.search_graph({ project: "ragflow", query: "community report extraction checkpoint structured output json parse", fields: ["lines"] });
// rank-2 checkpoints.community_checkpoint_key :39-40, rank-7 _get_text_output :192-208 (Go twin ParseCommunityReportChunks also surfaced as query-side spec)
```
**Probe:** No dedicated unit test for this extractor at the pin — evidence is full source read plus the active `test_checkpoints.py` covering the underlying save/load/cleanup it depends on. Coverage caveat recorded.

## Verdict
Adopt membership-sensitive checkpoint keys, the four-step brace-repair ladder, typed schema validation with drop-not-fail semantics, and singleton-skip; adapt report schema fields and prompt to your domain; omit pandas DataFrame intermediates (build CSV/JSON directly for your prompt format).
