<!-- capsule-v2 -->
# Index-build API entry — what contract turns a GraphRagConfig into collected pipeline run results?

**Source:** graphrag (MIT) `main@6dad6d2b059589624035714d8dcfde94ecc0a5fb`; Codebase Memory project `graphrag`. **Question:** How does a host drive indexing programmatically — callback wiring, update-mode method selection, and per-workflow error surfacing — without touching the CLI?

## build_index + _get_method — orchestration shell over run_pipeline
**Path/Symbol:** `packages/graphrag/graphrag/api/index.py`: `build_index` (:29-93), `_get_method` (:96-98). Imports pin collaborators: `create_callback_chain` (`graphrag.index.run.utils`), `PipelineFactory` (`graphrag.index.workflows.factory`), `run_pipeline` (`graphrag.index.run.run_pipeline`), `IndexingMethod` (`graphrag.config.enums`).
**Signature:** `async def build_index(config: GraphRagConfig, method: IndexingMethod | str = IndexingMethod.Standard, is_update_run: bool = False, callbacks: list[WorkflowCallbacks] | None = None, additional_context: dict[str, Any] | None = None, verbose: bool = False, input_documents: pd.DataFrame | None = None) -> list[PipelineRunResult]`.
**Data Shape:** consumes validated config (+optional caller-supplied DataFrame replacing document loading, surfaced to workflows as state key `additional_context`); emits one `PipelineRunResult` per workflow (result-or-error frame); returns the COLLECTED list after full drain.

### Decisive source
```python
# lifecycle symmetry: start → per-output branch → end
workflow_callbacks = create_callback_chain(callbacks) if callbacks else NoopWorkflowCallbacks()
method = _get_method(method, is_update_run)
pipeline = PipelineFactory.create_pipeline(config, method)
workflow_callbacks.pipeline_start(pipeline.names())
async for output in run_pipeline(pipeline, config, callbacks=workflow_callbacks, ...):
    outputs.append(output)
    if output.error is not None:
        workflow_callbacks.pipeline_error(output.error)   # error is DATA here, not an exception
    else:
        logger.info("Workflow %s completed successfully", output.workflow)
workflow_callbacks.pipeline_end(outputs)

def _get_method(method, is_update_run):
    m = method.value if isinstance(method, IndexingMethod) else method
    return f"{m}-update" if is_update_run else m
```

**Flow:** init_loggers(config,verbose) → chain-or-noop callbacks → method string resolved (update runs get the `-update` suffix) → factory builds the pipeline preset → start-callback carries workflow NAMES → async-collect outputs with per-output success/error logging → end-callback receives ALL outputs → return list.
**Invariant:** workflow errors NEVER abort the run — they surface as `output.error` data routed to `pipeline_error`, and the run still reaches `pipeline_end`. Update mode is encoded purely as a method-string suffix consumed downstream by the registry presets (see pipeline-factory-registry capsule). PROBED: `IndexingMethod` members themselves are `['standard','fast','standard-update','fast-update']`; `_get_method('custom', True)` → `'custom-update'`.
**Probe:** no dedicated unit test for api/index.py (recorded caveat: workflow-level smoke only upstream). Deterministic probe EXECUTED pre-write via lane venv: `_get_method(IndexingMethod.Standard, True) == 'standard-update'`, `_get_method(IndexingMethod.Standard, False) == 'standard'` — both observed true. Ghost-doc caveat: build_index docstring still documents a removed `memory_profile` parameter.

## Get live surrounding code
**Retrieve:** (executed live; rank-line-exact)
```ts
await mcp.codebase_memory.search_graph({ project: "graphrag", query: "build_index pipeline callbacks IndexingMethod update", limit: 10 });
// ranks: WorkflowCallbacks.pipeline_start/pipeline_end/pipeline_error :19-41 (callbacks plane),
// NoopWorkflowCallbacks twins :14-18 — the exact lifecycle build_index drives
```

## Verdict
Adopt collect-don't-abort error semantics, the three-point callback lifecycle, and suffix-encoded update selection. Adapt method vocabulary and result frames to host pipelines. Omit the CLI-facing conveniences. Coverage caveat: behavior beyond `_get_method` is source-verified only (no direct unit suite at this seam).
