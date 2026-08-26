<!-- capsule-v2 -->
# Code route — repo vs file granularity and the Enola graph task

**Source:** cognee (Apache-2.0) `main@a8f9760b`; Codebase Memory `ext-cognee`. **Question:** How does a knowledge pipeline ingest source code at two granularities (whole repos vs individual files) without mixing their task lists?

## get_code_file_tasks / get_code_repo_tasks
**Path/Symbol:** `cognee/tasks/code_graph/code_files.py:get_code_file_tasks`, `cognee/tasks/code_graph/code_repo.py:get_code_repo_tasks` (:1-324); `cognee/tasks/code_graph/enola.py` (:1-297); extraction `extract_code_graph.py` (:1-926).
**Signature:** `get_code_file_tasks()` / `get_code_repo_tasks()` — SYNC factories returning concrete lists (required by the per-item resolver contract; cognify.py :314-315 calls them WITHOUT await, unlike the async DLT factory).
**Data Shape:** `CodeFileDocument` → CODE route; `CodeRepoDocument` → CODE_REPO route; routing fact stamped at add time from `system_metadata`/extension.

### Decisive source
```python
tasks_by_route = {
    CognifyRoute.STANDARD: tasks,
    CognifyRoute.DLT_SOURCE: await get_dlt_tasks(...),
    CognifyRoute.CODE: get_code_file_tasks(),      # sync — no LLM-config dependency
    CognifyRoute.CODE_REPO: get_code_repo_tasks(),
}
```

**Flow:** code documents bypass TextChunking semantics — `extract_code_graph` parses AST/import structure into code entities and relations (`enola.py` drives the repo-level pass over the file graph), then results flow through the SAME add_data_points storage path as text pipelines. Repo manifests fan out to per-file processing with repo-scoped identity so file entities remain attributable to their repo node.
**Invariant:** (1) The two code routes exist because repo-level passes need cross-file state that per-file tasks must not recompute — merging them either duplicates work or leaks state across datasets. (2) Sync factories are part of the resolver contract (a list built once up front; validation dedups by list id). (3) Code entities still flow through deterministic DataPoint identity, so a function re-parsed later merges rather than duplicates.
**Probe:** `cognee/tests/unit/modules/retrieval/code_retriever_test.py`; routing pins `test_code_file_routes_to_code` / `test_code_repo_manifest_routes_to_code_repo` / `test_code_extension_without_tag_routes_standard` in `test_cognify_single_logical_run.py`.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "ext-cognee", query: "get_code_file_tasks get_code_repo_tasks enola extract_code_graph", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt dual-granularity code routes feeding shared storage; adapt AST parsing to your languages; omit Enola specifics unless porting repo-scale analysis.
