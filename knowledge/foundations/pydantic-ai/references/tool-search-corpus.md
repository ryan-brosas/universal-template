<!-- capsule-v2 -->
# Tool-search toolset — deferred tools, corpus membership, and the reveal ledger

**Source:** pydantic-ai (MIT) `main@b3cdbc96796f0294f1ac6943cdba70d14af8a0ef`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** When a large toolset hides tools behind `defer_loading=True`, how does the wrapper decide what is hidden vs searchable, when is the `search_tools` function emitted, and how are discoveries recovered from history?

## ToolSearchToolset.get_tools + discovery parsing
**Path/Symbol:** `pydantic_ai_slim/pydantic_ai/toolsets/_tool_search.py:ToolSearchToolset` (275-429), `keywords_search_fn` (109-129), `discovered_tool_names_in_order` (224-259).
**Signature:** `async get_tools(ctx) -> dict[str, ToolsetTool]`; `_search_tools(tool_args, ctx, search_tool) -> ToolSearchReturnContent`.
**Data Shape:** partitions wrapped tools into `visible` / `deferred`; searchable subset stamped `with_native='tool_search'`; `_SearchTool` carries `corpus: list[ToolDefinition]` + `revealed_tool_names: set[str]`.

### Decisive source
```python
for name, tool in all_tools.items():
    (deferred if tool.tool_def.defer_loading else visible)[name] = tool
if not deferred: return all_tools                       # nothing to manage -> no-op
if _SEARCH_TOOLS_NAME in all_tools: raise UserError(...) # reserved name

result = dict(visible)
for name, tool in deferred.items():
    if is_gated_by_deferred_capability(ctx, tool.tool_def):
        result[name] = tool            # capability-gated: reached by LOADING, never by search
    else:
        searchable[name] = tool
        result[name] = replace(tool, tool_def=replace(
            tool.tool_def, with_native=_TOOL_SEARCH_BUILTIN_ID))  # corpus membership ONLY

# emit local fallback only if enabled AND corpus non-empty; carries unless_native='tool_search'
# so adapters drop it when the provider runs the builtin server-side. Kept across steps to
# preserve the prompt-cache prefix even after everything is discovered.
if self.enable_fallback and searchable:
    result[_SEARCH_TOOLS_NAME] = self._build_search_tool(ctx, searchable)

# --- call time ---
if not any(q.strip() for q in queries): raise ModelRetry('Please provide at least one non-empty search query.')
scored_matches.append((tool_def.name not in search_tool.revealed_tool_names, score, {'name': ...}))
scored_matches.sort(key=lambda item: (item[0], item[1]), reverse=True)  # undiscovered FIRST,
matches = [m for _, _, m in scored_matches[: self.max_results]]         # relevance only tiebreaks
# empty result is a shaped VALUE, not an error: {'discovered_tools': [], 'message': _NO_MATCHES_MESSAGE}
```

**Flow:** wrap-time partition → stamp corpus membership on ungated deferred tools → conditionally emit `search_tools` → at call time tokenize queries+names/descriptions on `[a-z0-9]+` runs → score by set-overlap → sort undiscovered-first → trim to max_results → return typed content (never retry on zero matches). Discovery evidence for later steps/hosts is re-derived from history by scanning only the post-compaction window for `ToolAvailabilityDeltaPart` / `ToolSearchReturnPart` / native returns, plus a Pydantic-validated legacy `metadata['discovered_tools']` sideband — names in first-appearance order so provider tool segments stay byte-stable.
**Invariant:** `defer_loading` stays authored-set for the whole run; current visibility travels separately (`revealed_tool_names`). `with_native='tool_search'` means corpus membership and NOTHING else — capability-gated tools are never searchable. A no-match search returns normally and spends no retry; only blank/non-tokenizable queries raise ModelRetry. The search tool persists after full discovery (cache-prefix stability).
**Probe:** `tests/test_tool_search.py::test_tool_search_toolset_ranks_undiscovered_matches_first_when_trimmed` (890), `test_tool_search_toolset_does_not_match_substrings_inside_words` (803), `test_tool_search_toolset_keeps_search_tool_after_all_discovered` (1074), reserved-name collision at 1118.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "ToolSearchToolset defer_loading with_native discovered_tool_names keywords_search_fn", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the hidden-vs-searchable split, undiscovered-first ranking, and history-derived discovery ledger; adapt the tokenizer/scoring to your host's language; omit the native-builtin wire flags if your providers lack server-side tool search. Pairs with `capability-owned-toolset.md` (gating side). Coverage clean.
