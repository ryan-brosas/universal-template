<!-- capsule-v2 -->
# Incremental index pipeline — delta runs with timestamped child storage

**Source:** graphrag MIT `<branch>@<commit>`; Codebase Memory `graphrag`. **Question:** how does a heavy indexing pipeline support incremental updates (index only new documents, then merge) instead of full rebuilds?

## Connected graph-selected seam
**Path/Symbol:** `graphrag/index/run/run_pipeline.py`: `run_pipeline` (:30-116), `_copy_previous_output` (:182), `_dump_stats_json`/`_dump_context_json` (:160-181); workflows in `index/workflows/` (18 named steps: `load_input_documents`, `create_base_text_units`, `extract_graph`, `create_communities`, `create_community_reports`, `generate_text_embeddings`, `finalize_graph`, plus the `load_update_documents`/`update_*` variants); `index/run/profiling.py`: `WorkflowProfiler` context manager (:14).
**Signature:** `run_pipeline(pipeline, config, callbacks, is_update_run=False, additional_context?, input_documents?) -> AsyncIterable[PipelineRunResult]` — yields per-workflow results as it goes.
**Data Shape:** update layout = `{update_storage}/{timestamp}/delta` for new data + `{...}/{timestamp}/previous` backup of old output; persistent cross-run state lives in `context.json` inside output storage.

### Decisive source
```ts
state_json = await output_storage.get("context.json")
state = json.loads(state_json) if state_json else {}      # stateful workflows reload
if is_update_run:
    update_timestamp = time.strftime("%Y%m%d-%H%M%S")
    timestamped_storage = update_storage.child(update_timestamp)
    delta_storage = timestamped_storage.child("delta")     # new subset index
    previous_table_provider = update_table_provider.child("previous")
    await _copy_previous_output(output_table_provider, previous_table_provider)  # backup before merge
    if input_documents is not None:                        # direct-df fast path
        await delta_table_provider.write_dataframe("documents", input_documents)
        pipeline.remove("load_update_documents")           # skip the load step entirely
```

**Flow:** create storages/cache from config → load persisted state → standard run streams each workflow's result; update run first snapshots the previous output into a `previous/` child, indexes only new docs into a timestamped `delta/` child (later merged with the old index), and drops unneeded workflow steps from the pipeline when inputs arrive pre-loaded. Every workflow emits through the callback chain; stats/context dump to storage for observability.
**Invariant:** the previous index is always backed up BEFORE any merge; update runs write to a fresh timestamped namespace (never clobber); pipeline steps are removable by name when their input is pre-supplied; state survives runs via context.json.
**Probe:** `tests/` index tests (update run creates delta+previous children; pipeline.remove skips the step; context.json round-trips).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "graphrag", query: "run_pipeline is_update_run delta previous child WorkflowProfiler", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt timestamped child-storage deltas + previous-output backup + removable workflow steps for incremental indexing; adapt the workflow registry to host.
