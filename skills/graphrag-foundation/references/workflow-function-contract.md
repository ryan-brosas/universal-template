<!-- capsule-v2 -->
# Workflow function contract — what every `run_workflow(config, context)` must return and when it may stop the pipeline

**Source:** graphrag MIT `main@60668ba946ccfd5cb784c578efedff86798a2c35`; Codebase Memory project `graphrag`. **Question:** What is the uniform signature/return/error contract for a pipeline step, including the one legal early-stop mechanism?

## Key facts
**Path/Symbol:** `graphrag/index/typing/workflow.py` (`WorkflowFunction`, `WorkflowFunctionOutput`); all 22 built-ins in `graphrag/index/workflows/*.py` follow `async def run_workflow(config: GraphRagConfig, context: PipelineRunContext) -> WorkflowFunctionOutput`. The ONLY built-in that sets `stop=True`: `load_update_documents.py:42` (empty delta). State producers/consumers: `update_entities_relationships.py:53-55` writes `incremental_update_*` keys; `update_text_units.py:30` reads `context.state["incremental_update_entity_id_mapping"]`.
**Signature:** `WorkflowFunctionOutput(result=<json-safe payload|None>, stop=False)` — `result` is what `run_pipeline` logs/yields per step; `stop=True` halts remaining steps.
**Data Shape:** Cross-step data rides `context.state: dict[str, Any]`; durable artifacts ride `context.output_table_provider` tables; config-derived models are constructed per workflow via `create_completion(model_config, cache=context.cache.child(<instance_name>), cache_key_creator=cache_key_creator)`.

### Decisive source
```python
# load_update_documents.py :26-46 — guard + empty-delta early stop
if context.previous_table_provider is None:
    msg = "previous_table_provider is required for update workflows"
    raise ValueError(msg)                       # update steps REQUIRE previous output
...
if len(output) == 0:
    logger.warning("No new update documents found.")
    return WorkflowFunctionOutput(result=None, stop=True)   # nothing to merge → end run
await context.output_table_provider.write_dataframe("documents", output)
```
```python
# update_entities_relationships.py :53-55 — state handoff keys are namespaced by prefix;
# update_clean_state.run_workflow deletes EVERY key starting with "incremental_update_"
context.state["incremental_update_merged_entities"] = merged_entities_df
context.state["incremental_update_entity_id_mapping"] = entity_id_mapping
```
**Flow:** step reads inputs (DataReader or table streaming) → builds its LLM model with a namespaced cache child → produces artifacts → writes tables → returns samples/result; update steps additionally stash merge products into `context.state["incremental_update_*"]` for later steps, and `update_clean_state` (31L) sweeps those keys at pipeline end.
**Invariant:** `stop=True` only from the LOAD step on empty input — compute steps raise instead of stopping; `previous_table_provider is None` is an update-run precondition enforced by ValueError; `incremental_update_` prefix is a NAMESPACE CONTRACT (clean-state sweep would delete any key wearing it).
**Probe:** `tests/unit/indexing/update/test_update_relationships.py` (:68 merges old+delta, :120/:139/:158 orphan-source/target/both classification feeding the mapping chain); verbs-level `tests/verbs/test_update_text_embeddings.py` reuses `generate_text_embeddings` directly.
**Retrieve:** `await mcp.codebase_memory.search_graph({ project: "graphrag", query: "run_workflow WorkflowFunctionOutput stop incremental_update", limit: 10 })`

## Verdict
Adopt the two-argument signature, result-or-stop output object, and prefix-namespaced state keys swept by a terminal cleanup step. Never repurpose `stop=True` beyond "input produced nothing".
