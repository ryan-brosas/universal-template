<!-- capsule-v2 -->
# single-node-graph-subsetting — How does "run just this iteration node" work on a full workflow graph?

**Source:** dify Apache-2.0 `main@8bdf702f`; Codebase Memory `ext-dify`. **Question:** How do you execute one container node in isolation for debugging?

## Node/edge filtering by membership key, then Graph.init with skip_validation
**Path/Symbol:** `api/core/app/apps/workflow_app_runner.py:WorkflowBasedAppRunner._get_graph_and_variable_pool_for_single_node_run` (:240-395); entry `_prepare_single_node_execution` (:175-238).
**Signature:** `_get_graph_and_variable_pool_for_single_node_run(workflow, node_id, user_inputs, graph_runtime_state, node_type_filter_key: str, node_type_label = "node", *, user_id="", trace_session_id=None)`.
**Data Shape:** `node_type_filter_key` is `"iteration_id"` or `"loop_id"`; kept nodes = {target} ∪ {nodes whose data[key]==node_id} ∪ {declared start_node_id}; kept edges = both endpoints present or endpoint None.

### Decisive source
```python
main_node_config = next((n for n in graph_config.get("nodes", []) if n.get("id") == node_id), None)
start_node_id = main_node_config.get("data", {}).get("start_node_id") if main_node_config else None
node_configs = [
    node
    for node in graph_config.get("nodes", [])
    if node.get("id") == node_id
    or node.get("data", {}).get(node_type_filter_key, "") == node_id
    or (start_node_id and node.get("id") == start_node_id)
]
graph_config["nodes"] = node_configs

node_ids = [node.get("id") for node in node_configs]
edge_configs = [
    edge
    for edge in graph_config.get("edges", [])
    if (edge.get("source") is None or edge.get("source") in node_ids)
    and (edge.get("target") is None or edge.get("target") in node_ids)
]
graph_config["edges"] = edge_configs
...
graph = Graph.init(graph_config=graph_config, node_factory=node_factory, root_node_id=node_id, skip_validation=True)
```

**Flow:** debug request names a container node → subset its member nodes (membership recorded on each child's data during authoring) plus the virtual start → keep edges that survive with either end nulled → init graph rooted AT the container with validation skipped (the subset violates whole-graph assumptions like reachability) → preload selectors + extract variable mapping + map user inputs BEFORE init so constructor-time context exists.
**Invariant:** The filter key differs per container type but the algorithm is shared; `skip_validation=True` is mandatory for subsets (full-graph invariants don't hold); variable-pool loading happens against the FULL `workflow.graph_dict` mapping (extract_variable_selector receives the original config) while the EXECUTED graph is the subset — conflating the two configs is the classic port bug.
**Probe:** `grep -c 'node_type_filter_key' core/app/apps/workflow_app_runner.py` → 5; direct tests `tests/unit_tests/core/app/apps/test_workflow_app_runner_core.py::test_get_graph_and_variable_pool_for_single_node_run` (+`_includes_trace_session_id` twin).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-dify", query: "_get_graph_and_variable_pool_for_single_node_run iteration loop filter", limit: 10 });
```

## Verdict
Adopt subset-then-skip-validation for single-node debug execution. Adapt membership keys and whether you preload variables before init. Omit the RAG-pipeline variant (`pipeline_runner`) unless porting that product.
