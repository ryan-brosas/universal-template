<!-- capsule-v2 -->
# Context-pruning selection plane — how do you select and order the files an LLM sees, and how much of the "agentic pruning" module is actually alive?

**Source:** sweep (Apache-2.0) `main@a8b8b67bda4f`; Codebase Memory `sweep`. **Question:** In a 1080-line context-pruning module, which functions does the production ticket path actually execute, what are the selection/insertion semantics, and where is the dead agentic loop a porter must not copy?

## Live surface: parse_query_for_files → boost_snippets_to_top → build_import_trees → twin get_relevant_context
**Path/Symbol:** `sweepai/core/context_pruning.py:parse_query_for_files` (:602–630), `RepoContextManager.boost_snippets_to_top` (:301–311), `add_relevant_files_to_top_snippets` (:531–547), `build_import_trees` (:493–529), `build_full_hierarchy` (:334–381), `load_graph_from_file` (:384–399); live twin `sweepai/utils/ticket_utils.py:get_relevant_context` (:443–502), called from `fetch_relevant_files` (:505–563).
**Signature:** `parse_query_for_files(query: str, rcm: RepoContextManager) -> tuple[RepoContextManager, nx.DiGraph]` (returns `(rcm, None)` at pin); `build_full_hierarchy(graph, start_node, k, prefix="", is_last=True, level=0) -> str`.
**Data Shape:** `RepoContextManager` holds `current_top_snippets` (editable context), `read_only_snippets`, `relevant_file_paths` (files named in the user query), `snippet_scores`; the LLM file-selection step (`context_get_files_to_change`, sweep_bot.py:1021) returns file paths that become WHOLE-FILE snippets (start=0, end=len(content.split("\n"))).

### Decisive source
```python
# parse_query_for_files — full path OR uri-encoded OR last-two-parts (depth>=2, len>5)
elif len(file.split('/')) >= 2:
    last_two_parts = '/'.join(file.split('/')[-2:])
    if (last_two_parts in query or urllib.parse.quote(last_two_parts) in query) and len(last_two_parts) > 5:
        code_files_to_add.append((file, last_two_parts))
...
for code_file in code_files_to_add[:MAX_FILES_TO_ADD]:   # MAX_FILES_TO_ADD = 5
    rcm.append_relevant_file_paths(code_file)

# append_relevant_file_paths — REBINDS, never appends in place
def append_relevant_file_paths(self, relevant_file_paths: str):
    # do not use append, it modifies the list in place and will update it for ALL instances of RepoContextManager
    self.relevant_file_paths = self.relevant_file_paths + [relevant_file_paths]

# boost_snippets_to_top — insert AFTER the last query-mentioned file's first position
all_first_in_query_positions = [self.top_snippet_paths.index(file_path) for file_path in code_files_in_query if file_path in self.top_snippet_paths]
last_mentioned_result_index = (max(all_first_in_query_positions, default=-1) + 1) if all_first_in_query_positions else 0
self.current_top_snippets.insert(max(0, last_mentioned_result_index), snippet)

# context_pruning.get_relevant_context — the agentic loop is switched off
user_prompt = repo_context_manager.format_context(unformatted_user_prompt=unformatted_user_prompt, query=query)
return repo_context_manager # Temporarily disabled context
chat_gpt = ChatGPT()          # DEAD at pin: unreachable, and this function has zero production callers
```

**Flow:** fetch_relevant_files (@streamable) → prep_snippets.stream yields ranked snippets into a fresh RepoContextManager → parse_query_for_files (match every repo file by full path / URI-encoded form / last-two-parts; sort by position-in-query; dedupe; cap 5) → add_relevant_files_to_top_snippets (boost each query-named file's snippets to just after the last query-named file's first occurrence — a protected prefix zone) → ticket_utils.get_relevant_context: build_import_trees (per query-file, or top-5 snippets if none, render a 2-level box-drawing import hierarchy via build_full_hierarchy — sorted successors, predecessors PREPENDED at root, fail-soft partial return on nx errors — plus read_only paths as "may contain helpful services") → add_relevant_files_to_top_snippets again → context_get_files_to_change (LLM picks relevant + read-only files) → rebuild both snippet lists as whole-file snippets with FileNotFoundError-skip → if BOTH lists empty, restore the deepcopy taken before the LLM call.
**Invariant:** The empty-fallback restore means the LLM file-selection step can NEVER return an empty context — a port must keep the pre-LLM snapshot and the both-empty check or one bad LLM response wipes the ticket's context. The rebind-not-append in append_relevant_file_paths exists because RepoContextManager instances share lists across stream snapshots; in-place mutation would leak state between yielded snapshots. Query-named files must stay ahead of search-ranked ones (insert-after-last-mentioned, not append). DEAD AT PIN — do not port: context_pruning.get_relevant_context (early return "# Temporarily disabled context" AND zero production callers), the whole Claude rollout loop (handle_function_call :746, perform_rollout :965, context_dfs :1019, search_for_context_with_reflection :949, validate_and_parse_function_calls), graph_retrieval/integrate_graph_retrieval (personalized-pagerank TF-IDF-style distillation + listwise rerank — call sites commented out at :474/:504/ticket_utils.py:535). The only live imports from the module are ticket_utils.py:18: RepoContextManager, add_relevant_files_to_top_snippets, build_import_trees, parse_query_for_files.
**Probe:** `tests/test_context_pruning.py` (50L) executed at pin → FAILED (errors=1) at import: ModuleNotFoundError networkx (chain also needs scipy/numpy; all absent from system python). Its three tests: test_build_full_hierarchy is pure/offline (exact box-drawing expectation over a 4-edge DiGraph) but unrunnable here; test_load_graph_from_file references fixture `tests/test_import_tree.txt` which DOES NOT EXIST at pin; test_get_relevant_context uses `ClonedRepo` without importing it (NameError even with credentials) and needs GITHUB_PAT + live clone — stale. Deterministic probes at pin: `grep -n 'Temporarily disabled context' sweepai/core/context_pruning.py` → :662; `grep -n 'MAX_FILES_TO_ADD = 5'` → :605; `grep -n 'from sweepai.core.context_pruning import' sweepai/utils/ticket_utils.py` → :18 (the only production importer); `grep -rn 'integrate_graph_retrieval\|graph_retrieval(' --include='*.py' sweepai/` → only defs + commented call sites; `grep -rn 'context_dfs\|perform_rollout' --include='*.py' sweepai/ | grep -v 'def '` → only intra-module refs downstream of the early return.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "sweep", query: "parse_query_for_files boost_snippets_to_top build_full_hierarchy RepoContextManager", limit: 10 });
// NOT executed this session (Codebase Memory MCP not connected); direct source reads of
// context_pruning.py (1080L whole) + ticket_utils.py:440-563 at pin substituted — see verification.md pass 4.
```

## Verdict
Adopt the query-file matching ladder (full path / URI-encoded / last-two-parts with length floor, position-sorted, capped), the protected-prefix insertion after the last query-mentioned file, the rebind-not-append shared-list discipline, the 2-level box-drawing hierarchy with predecessors-at-root and fail-soft partial rendering, and the pre-LLM snapshot + both-empty restore so file selection can never empty the context. Adapt the whole-file snippet rebuild to your chunking model. Omit the entire dead agentic loop (rollouts, reflections, Claude function-call parsing, pagerank graph retrieval) — it is unreachable at pin and its prompts/tools are product-specific. Coverage caveat: no runnable direct test at pin (networkx/scipy/numpy missing; one fixture file absent; one test stale).
