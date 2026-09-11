<!-- capsule-v2 -->
# Dry-run cost estimation — cognify's token/cost forecast without side effects

**Source:** cognee (Apache-2.0) `main@a8f9760b`; Codebase Memory `ext-cognee`. **Question:** How do you estimate an LLM pipeline's token usage and cost per stage WITHOUT executing it or polluting state?

## estimate_cognify_dry_run
**Path/Symbol:** `cognee/modules/cognify/estimator.py:estimate_cognify_dry_run` (module 598L; entry via `cognify(dry_run=True)` at cognify.py :260-272).
**Signature:** `await estimate_cognify_dry_run(datasets, user=..., graph_model=..., chunker=..., chunk_size=None, custom_prompt=None) -> DryRunEstimate`.
**Data Shape:** Stage-level estimate covering ALL data in the selected datasets; a real incremental run may process FEWER items (documented on the parameter).

### Decisive source
```python
if dry_run:
    if temporal_cognify:
        raise ValueError("dry_run is supported for the default cognify pipeline only.")
    from cognee.modules.cognify.estimator import estimate_cognify_dry_run
    return await estimate_cognify_dry_run(datasets, user=user, graph_model=graph_model,
                                          chunker=chunker,
                                          chunk_size=chunk_size or await get_max_chunk_tokens(),
                                          custom_prompt=custom_prompt)
```

**Flow:** dry_run checked BEFORE task-list construction and BEFORE the pipeline executor; estimator reuses the SAME routing module (`cognify_route_for`) so cost estimates can never drift from execution — that shared pure router is the load-bearing design choice (routing.py docstring names the estimator as a required consumer). Chunk-size default matches the real path (`get_max_chunk_tokens()`), so chunk counts projected match production chunking.
**Invariant:** (1) An estimate must be SIDE-EFFECT FREE: no LLM calls, no graph writes, no status markers — anything the estimator writes would corrupt the next real run's incremental skips. (2) Estimation scope honesty: full-dataset numbers are returned even when the actual run would skip already-processed items — surfaced to the caller rather than silently under-reporting. (3) Remote-client mode rejects dry_run outright (`dry_run is not supported while connected to a remote Cognee instance`) because the remote cannot guarantee local-state fidelity.
**Probe:** `cognee/tests/unit/modules/cognify/test_estimator.py` (whole file).

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "ext-cognee", query: "estimate_cognify_dry_run DryRunEstimate token cost", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt estimate-before-tasks gating + routing-shared projection + explicit scope caveats; adapt token accounting to your LLM gateway; omit remote-mode rejection if you have no split control/data plane.
