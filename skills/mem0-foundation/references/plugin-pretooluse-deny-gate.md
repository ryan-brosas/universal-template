<!-- capsule-v2 -->
# PreToolUse deny gate — how does a hook veto a tool call and turn the rejection itself into guidance?

**Source:** mem0 Apache-2.0 `main@7e096155714c`; Codebase Memory `mem0`. **Question:** when a plugin must forbid certain file writes (here: memory files, to force all memory through the memory API), what is the minimal veto contract that both blocks the call and coaches the agent in the same gesture?

## block_memory_write.sh — exit-code deny with stderr feedback
**Path/Symbol:** `integrations/mem0-plugin/scripts/block_memory_write.sh` (36L; hooks.json PreToolUse matcher `Write|Edit|MultiEdit`, no timeout override).
**Signature:** stdin JSON `{tool_name, tool_input}` → exit 0 (allow) | exit 2 (block; stderr is shown to the agent as the rejection reason).
**Data Shape:** reads exactly one field — `.tool_input.file_path // .tool_input.path // ""` via jq with `|| echo ""` fallback; empty path allows.

### Decisive source
```bash
# Exit codes:
#   0 = allow the tool call
#   2 = block the tool call (stderr is shown to Claude as feedback)
set -euo pipefail
...
case "$FILE_PATH" in
  */.claude/*/MEMORY.md|*/.claude/memory/*)
    echo "BLOCKED: Do not write to $FILE_PATH. Use the mem0 MCP \`add_memory\` tool instead to persist memories. This project uses mem0 for all memory storage." >&2
    exit 2
    ;;
  *)
    exit 0
    ;;
esac
```

**Flow:** parse file_path from tool_input → glob-match against the protected memory-file family (`*/.claude/*/MEMORY.md`, anything under `*/.claude/memory/`) → on match print a redirect message to STDERR naming the sanctioned alternative tool and exit 2; everything else exits 0.
**Invariant:** the deny is expressed ONLY by exit code 2 + stderr text; any other failure mode must not fabricate a denial — hence this guard uses `set -euo pipefail` WITH `-e` (the opposite choice from the prompt hook's deliberate `-e`-omission): a jq or parse crash exits 1, which the host treats as a non-blocking hook error rather than a silent allow-with-corrupted-input or a false block. The block message must name the replacement primitive (`mem0 MCP add_memory`) so the veto doubles as routing.
**Probe:** no dedicated pytest file exists for this script (honest gap). Deterministic probe executed this pass: byte-exact grep of the two contract lines (`exit codes` header + `exit 2` case arm) and of the hooks.json matcher `"matcher": "Write|Edit|MultiEdit"` binding it; sibling coverage lives in `tests/test_write_path.py::test_no_metadata_project_id_anywhere`, which pins the same "all memory goes through mem0 writes with proper metadata" policy at the API layer.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase-memory.search_graph({ project: "mem0", query: "block memory write guard metadata defaults enforce", limit: 10 });
```
Executed live: returns `test_write_path.test_no_metadata_project_id_anywhere` and mem0-core write-path nodes; bash guards have no graph Function nodes, so source+hooks.json are the citation surface.

## Verdict
Adopt the three-value exit grammar (allow / block-with-feedback / error-is-not-block) and the "deny message names the sanctioned path" pattern; adopt the matcher-scoped registration (only Write/Edit/MultiEdit pay the jq cost). Adapt the protected-path globs and the redirect target to your host's memory tool. Omit nothing else — the script is deliberately total. Coverage: file fully indexed, read whole; no direct-test runner exists for it (recorded as an honest gap, deterministic probes only).
