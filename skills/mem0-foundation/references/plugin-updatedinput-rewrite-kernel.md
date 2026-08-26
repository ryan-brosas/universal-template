<!-- capsule-v2 -->
# updatedInput rewrite kernel — how does a hook transparently complete an agent's half-specified tool call instead of rejecting it?

**Source:** mem0 Apache-2.0 `main@7e096155714c`; Codebase Memory `mem0`. **Question:** when an agent calls memory tools with missing identity/metadata, how do you inject the defaults server-side-of-the-tool (rewriting input before execution) without ever corrupting a call that was already correct?

## enforce_metadata_defaults.sh — compute patch, emit only when changed
**Path/Symbol:** `integrations/mem0-plugin/scripts/enforce_metadata_defaults.sh` (218L; hooks.json PreToolUse matcher `mcp__mem0__.*|mcp__plugin_mem0_mem0__.*`, timeout 3).
**Signature:** bash dispatch on `.tool_name` → heredoc python over env-passed `_MEM0_TOOL_INPUT/_MEM0_USER_ID/_MEM0_APP_ID/_MEM0_GLOBAL_SEARCH/_MEM0_HANDLER` → prints patched JSON only when something changed → shell re-emits via `jq -n --argjson` as `{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"allow","updatedInput":...}}`.
**Data Shape:** four handlers: add_memory & delete_all_memories take TOP-LEVEL user_id/app_id; search_memories/get_memories take filter-list identity; metadata defaults apply to add_memory only.

### Decisive source
```python
    # Track session in metadata instead of run_id.
    # run_id creates a separate entity partition in the v3 API,
    # making memories invisible to search/get_memories calls
    # that don't include a run_id filter.
    if "session_id" not in meta:
        sid = os.environ.get("MEM0_SESSION_ID", "")
        if not sid:
            session_file = "/tmp/mem0_session_id_" + os.environ.get("USER", "default")
            ...
        if sid:
            meta["session_id"] = sid
            changed = True
```
Filter injection handles all three shapes separately: no `filters` → build `{"AND":[{"user_id":uid},{"app_id":aid}]}`; flat dict (`{"user_id":"x"}`) → convert each existing key to a clause and append missing identity; `AND` list → append missing clause dicts after an `any("user_id" in c ...)` check.

**Flow:** match tool name (both `mcp__mem0__*` and plugin-scoped aliases) → read tool_input → python computes per-field: inject top-level identity when absent and truthy; metadata defaults `confidence=0.7`, `files=["*"]`, `source="auto_capture"`, `type="task_learning"`; `confidence>=1.0` forces `infer=False` (verbatim storage skips LLM extraction); session id from env else `/tmp/mem0_session_id_$USER` goes into METADATA; global-search mode rewrites filters to `{"OR":[{"user_id":"*"}]}` → write patch to `/tmp/mem0_enforce_$$` (EXIT-trap removed) → shell validates with `jq empty` and emits updatedInput envelope ONLY if non-empty and parseable → background `session_stats.py add|search` records usage HERE because PostToolUse hooks don't fire for plugin MCP tools.
**Invariant:** never mutate what's already specified (every injection is gated on absence), never emit a malformed envelope (patch must pass `jq empty`; failures fall through to plain allow with original input), and never put scoping in `run_id` — it partitions entities in the v3 API so memories become invisible to searches lacking a run_id filter; metadata.session_id carries the correlation instead. The whole rewrite must fit the host's 3s timeout.
**Probe:** no dedicated pytest file for this script (honest gap). Deterministic probes executed this pass: byte-exact greps of the run_id-partition comment block and of `"updatedInput": $updated` emission; hooks.json binding check (matcher regex + timeout 3). The downstream shape it produces IS test-pinned: `tests/test_search.py` pins the AND-scoped/OR-global filter dialect this script writes.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase-memory.query_graph({ project: "mem0", query: "MATCH (a)-[r:CONFIGURES]->(b) WHERE a.file_path CONTAINS 'mem0-plugin' OR b.file_path CONTAINS 'mem0-plugin' RETURN a.name, labels(a), b.name, b.file_path LIMIT 30" });
```
Executed live: CONFIGURES edges resolve to env-var→api_key maps in plugin manifests (hook wiring itself is textual); combined with `search_graph` "block memory write guard metadata defaults enforce" which surfaces the write-path policy tests.

## Verdict
Adopt the absent-gated injection matrix, the changed-only patch emission with jq validation, and above all the metadata-not-run_id session correlation rule (a port that copies session→run_id will silently partition memories away from search). Adapt handler names/defaults vocabulary to your tool surface. Omit the mem0-specific confidence/infer coupling unless your backend has a verbatim-vs-extracted distinction. Coverage: file fully indexed, read whole (218L); no direct-test runner exists for the script itself — recorded, deterministic evidence only.
