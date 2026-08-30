<!-- capsule-v2 -->
# WorkspaceFilesystem tool surface — never-raise error funnel and the LLM-tools vs transfer-plumbing split

**Source:** cuga-agent Apache-2.0 `main@5de53ade`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** Which filesystem operations become LLM tools, how do failures reach the model, and why do `search_files`/`edit_file` return the shapes they do?

## The 8-tool surface + error contract
**Path/Symbol:** `src/cuga/backend/cuga_graph/nodes/cuga_lite/executors/filesystem/workspace_fs.py` (`as_structured_tools` :261-336; `search_files` :227-234; `_apply_slice_and_grep` :32-62; `_apply_file_edits` :65-87; module factories `create_filesystem_tools` :343-355, `get_transfer_callables` :358-365).
**Signature:** 8 StructuredTools: `read_file(path, start_line?, end_line?, grep_pattern?)`, `write_file(path, content)`, `edit_file(path, edits: [{oldText,newText}], dryRun=False)`, `list_files(path=".", pattern="*")`, `make_directory(path)`, `move_file(source, destination)`, `search_files(path, pattern, excludePatterns?)`, `get_file_info(path)`.
**Data Shape:** Every tool catches ALL exceptions and returns `[<tool>_error] <exc>` strings. `list_files` returns backend `ListFilesResult.model_dump_json()` (`{sandbox_path, entries:[{name,path,is_dir,size_bytes}]}`). `search_files` returns ONE newline string; empty string = no matches. `read_file` slice+grep: lines prefixed `N|` only when grepping; past-end start returns an explanatory message, not an error.

### Decisive source
```python
# :229-232 — falsy-empty is a CONTRACT, documented in the tool description
results = await self.backend.search(path, pattern, excludePatterns or [])
# Empty string (not e.g. "No matches found") so callers can rely on
# falsiness to detect "nothing found" instead of indexing into it like a list.
return "\n".join(results) if results else ""

# :71-75 — edit engine: unique-match enforcement with counts in the error
if old_text not in content:
    raise ValueError(f"Text to replace not found: {old_text[:50]}...")
count = content.count(old_text)
if count > 1:
    raise ValueError(f"Text appears {count} times, must be unique: {old_text[:50]}...")

# docstring of as_structured_tools — download/upload are deliberately NOT returned
```

**Flow:** read_file applies line-slice (1-based inclusive, clamped) then per-line regex (invalid pattern → error string), numbering output ONLY when a grep filter ran → write_file validates `.py` (see fs-python-write-validation) then writes via backend, auto-creating parents → edit_file reads, applies edits sequentially (each oldText must match exactly once; multiple sequential edits apply cumulatively), skips the write when unchanged or dryRun, and renders a zip-based `- / +` diff prefixed by status → move refuses existing destinations at the BACKEND (`ValueError`) → search dispatches: `**` in pattern → recursive glob with three-way fnmatch exclude (rel, `**/{ex}`, `**/{ex}/**`); otherwise single-level sorted listdir.
**Invariant:** download/upload are host↔sandbox TRANSFER plumbing — callable methods plus module functions, but never members of `as_structured_tools()` (pinned by test asserting exact 8-name set). The no-match sentinel must remain `""`: any humanized "No matches found" breaks every agent that does `if not result:`. Backend exceptions are part of the tool's data channel, not control flow.
**Probe:** direct tests `filesystem/tests/test_workspace_fs.py::test_factory_returns_eight_named_tools` (:262), `::test_download_upload_callable_but_not_structured_tools` (:229 asserts names == exact set AND round-trips), `::test_edit_file_unique_match_diff_and_dryrun` (:174), `::test_search_files_and_get_file_info` (:209 asserts `none_found == "" and not none_found`), `::test_write_read_round_trip_and_slicing` (:144 asserts `"3|l3"`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "WorkspaceFilesystem as_structured_tools _apply_file_edits search_files create_filesystem_tools", limit: 10 });
```

## Verdict
Adopt the closed 8-tool LLM surface with transfer callables kept off it, the `[tool]_error]` string funnel, unique-match-or-error edit engine with cumulative multi-edits and dry-run diff, and the empty-string no-match contract. Adapt tool descriptions to your agent's conventions but keep the falsiness guidance IN the description (agents read it). Omit MCP wrapping — this surface is deliberately plain StructuredTools ("no MCP").
