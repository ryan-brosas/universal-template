<!-- capsule-v2 -->
# Pipeline factory & method registry — how do named workflows assemble into selectable index pipelines?

**Source:** graphrag MIT `main@60668ba946ccfd5cb784c578efedff86798a2c35`; Codebase Memory project `graphrag`. **Question:** How do you expose a fixed set of pipeline stages so hosts can pick standard/fast/update pipelines AND inject custom workflows without forking the runner?

## Key facts
**Path/Symbol:** `graphrag/index/workflows/factory.py` (`PipelineFactory` :17-48; class-var registries `workflows: dict[str, WorkflowFunction]` / `pipelines: dict[str, list[str]]` :20-21; `register` :23-26, `register_all` :28-32, `register_pipeline` :34-37, `create_pipeline` :39-48); default pipelines `_standard_workflows`/_fast_workflows/_update_workflows :52-83; registration calls :84-97. Registration of implementations lives in `index/workflows/__init__.py` (`PipelineFactory.register_all({...})` :77-100 — importing the package is what populates the registry).
**Signature:** `create_pipeline(config, method: IndexingMethod | str = Standard) -> Pipeline` where `Pipeline = list[tuple[str, WorkflowFunction]]`.
**Data Shape:** `config.workflows` (optional user override list of names) > `cls.pipelines[method]` (named preset) — resolution is ONE line (:46): `workflows = config.workflows or cls.pipelines.get(method, [])`.

### Decisive source
```python
# factory.py :40-48 — custom-workflow injection is just dict mutation on the ClassVar
@classmethod
def create_pipeline(cls, config, method=IndexingMethod.Standard) -> Pipeline:
    workflows = config.workflows or cls.pipelines.get(method, [])
    logger.info("Creating pipeline with workflows: %s", workflows)
    return Pipeline([(name, cls.workflows[name]) for name in workflows])

# factory.py :90-93 — update pipelines CONCAT base flows then update flows;
# order matters: merges consume state keys produced by earlier steps
PipelineFactory.register_pipeline(
    IndexingMethod.StandardUpdate,
    ["load_update_documents", *_standard_workflows, *_update_workflows],
)
```
The four presets: Standard = `load_input_documents` + 9 standard steps; Fast swaps `extract_graph`→`extract_graph_nlp` + `prune_graph`, and `create_community_reports`→`create_community_reports_text`; both Update variants prepend `load_update_documents` then append the 8 `update_*` steps AFTER the standard ones (merges need freshly built delta artifacts).
**Flow:** host imports `graphrag.index.workflows` (side-effect registers everything) → optionally `PipelineFactory.register("custom", fn)` / `register_pipeline("mine", [...])` → `create_pipeline(config, method)` resolves name list → runner executes the `(name, fn)` pairs sequentially.
**Invariant:** unknown workflow name raises KeyError at PIPELINE CREATION (fail fast before any IO); a custom `config.workflows` list REPLACES the preset wholesale (no merge); update-pipeline correctness depends on step ORDER (state producers precede consumers) — never reorder.
**Probe:** no dedicated unit test for factory.py at this HEAD — pinned by `tests/unit/graphrag_factory/test_factory.py` (GraphRag factory construction) plus every pipeline integration path exercising `create_pipeline`; coverage caveat recorded here.
**Retrieve:** `await mcp.codebase_memory.search_graph({ project: "graphrag", query: "PipelineFactory register_pipeline create_pipeline workflows", limit: 10 })`

## Verdict
Adopt the two-ClassVar registry (names→fns, methods→name-lists) and the `config.workflows or preset` single-line precedence; adapt enum/method naming. The KeyError-at-creation contract and concat-order of update pipelines are load-bearing.
