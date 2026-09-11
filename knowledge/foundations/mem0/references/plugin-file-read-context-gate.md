<!-- capsule-v2 -->
# File-read context injection gate — how do you inject memory context before a Read without ever blocking or slowing it?

**Source:** mem0 Apache-2.0 `main@7e096155714c`. **Question:** when an agent-memory plugin wants to show "prior work on this file" the moment the agent opens it, how does it keep the Read fast and unblockable while still searching a remote memory API?

## Read-hook worker with size gate (file_context.py)
**Path/Symbol:** `integrations/mem0-plugin/scripts/file_context.py:gate_file` (lines 40–54) + `search_file_context` (92–107) + `main` (109–133); wired by `scripts/on_file_read.sh` (PreToolUse matcher Read).
**Signature:** `gate_file(file_path: str, cwd: str) -> str | None`; `search_file_context(api_key, user_id, project_id, file_path, cwd) -> str`.
**Data Shape:** constants `FILE_READ_GATE_MIN_BYTES = 1500`, `MAX_RESULTS = 5`, `SEARCH_TIMEOUT = 5`; search body top_k=5 threshold=0.3, query = `"{rel} {basename}"` (rel = cwd-relative path) or just rel when the file sits in cwd; `MEM0_GLOBAL_SEARCH=true` flips to global search.

### Decisive source
```python
def gate_file(file_path: str, cwd: str) -> str | None:
    """Return the resolved absolute path if the file passes gating, else None."""
    if not file_path:
        return None
    p = Path(file_path)
    if not p.is_absolute():
        p = Path(cwd) / p
    try:
        p = p.resolve()
        if not p.is_file():
            return None
        if p.stat().st_size < FILE_READ_GATE_MIN_BYTES:
            return None
        return str(p)
    except OSError:
        return None
```
The shell wrapper owns the JSON envelope, not the worker:
```bash
TIMELINE=$(python3 "$SCRIPT_DIR/file_context.py" "$FILE_PATH" "$CWD" 2>/dev/null || echo "")
if [ -z "$TIMELINE" ]; then exit 0; fi
jq -cn --arg ctx "$TIMELINE" '{ hookSpecificOutput: { hookEventName: "PreToolUse",
  additionalContext: $ctx, permissionDecision: "allow" } }'
```
**Flow:** PreToolUse(Read) → wrapper jq-extracts `tool_input.file_path` (empty ⇒ exit 0) → resolves MEM0_API_KEY via `_identity.sh` fallback (Desktop users get it from shell profile) → worker `main`: no argv ⇒ exit 0; no api_key ⇒ exit 0; gate fails ⇒ exit 0; search returns nothing ⇒ exit 0 — every failure path is a SILENT exit 0, the Read always proceeds. Success path prints plain-text timeline lines `- {icon} [{cat}] ({age}) {text≤150} [mem0:{id8}]` and the wrapper re-wraps as `additionalContext` with `permissionDecision: "allow"`.
**Invariant:** the Python worker NEVER emits JSON and NEVER emits errors — the division of labor is "worker = text or nothing, wrapper = envelope or exit 0". The 1500-byte gate keeps tiny files (configs, snippets) from paying a 5s network round trip; `Path.resolve()` + `is_file()` absorbs symlinks and nonexistent paths without exceptions escaping. `main()` is wrapped in `try/except Exception: pass` + unconditional `sys.exit(0)` — a hook that can block the Read is worse than one that shows nothing.
**Probe:** no dedicated test file for file_context.py (honest gap); byte-exact grep probes executed this pass: `FILE_READ_GATE_MIN_BYTES = 1500` (1 hit), `permissionDecision: "allow"` in on_file_read.sh (1 hit), `additionalContext` (1 hit). Behavior contract is pinned by the silent-exit-0 structure read directly from both files.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mem0", query: "file context read hook gate timeline", limit: 10, fields: ["signature", "lines"] });
```
Recorded for graph-connected sessions: Codebase Memory MCP was NOT connected this pass (env ref unavailable) — DEGRADED evidence path; both source files read whole directly instead, per AGENTS.md fallback.

## Verdict
Adopt the gate-before-network ladder (empty path → not-a-file → under-size → silent exit 0) and the worker-text/wrapper-JSON split for any PreToolUse context injection — it makes the injection strictly additive to tool latency. Adapt the 1500-byte threshold and top-5/threshold-0.3 search shape to your memory store. Omit the mem0 cloud endpoint/auth shape. Coverage: both cited paths read whole this pass; no dedicated tests exist (recorded gap, grep probes GREEN).
