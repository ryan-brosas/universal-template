<!-- capsule-v2 -->
# Tool-name resolution + internal-search vocabulary — how do hooks get the LLM-facing name from a registry path, and who owns "has search"?

**Source:** pipeshub-ai Apache-2.0 @ `main` (pin `6850972`); Codebase Memory `mnt-hdd-utopia-inspo-platforms-pipeshub-ai`. **Question:** hooks see `/tools/jira/search_issues` paths while the model sees `jira__search_issues` — where does translation live and why is the legacy name set a frozenset of FOUR spellings?

## Registry-first resolution with path fallback; one shared vocabulary constant
**Path/Symbol:** `backend/python/app/agents/agent_loop/hooks/_tool_naming.py:17-47` (`resolve_tool_name`, `INTERNAL_SEARCH_TOOL_NAMES`, `INTERNAL_SEARCH_DELEGATE_NAME/FLAT_NAME`).
**Signature:** `resolve_tool_name(ctx: ToolCallContext | ToolResultContext) -> str`; `INTERNAL_SEARCH_TOOL_NAMES: frozenset[str]`.
**Data Shape:** consumed by result_accumulation, ask_user_question, and citations' `_grant` gate — three hooks, zero re-derivations.

### Decisive source
```python
def resolve_tool_name(ctx):
    """Resolves through the registry rather than re-deriving the name from
    the path string, so this stays correct if path structure ever changes."""
    registry = ctx.scope.turn.run.runtime.tool_registry if ctx.scope is not None else None
    if registry is not None and registry.has_path(ctx.tool_path):
        return registry.resolve(ctx.tool_path).name
    segments = [s for s in ctx.tool_path.split("/") if s]
    return "_".join(segments[-2:]) if len(segments) >= 2 else ctx.tool_path

INTERNAL_SEARCH_TOOL_NAMES = frozenset({
    INTERNAL_SEARCH_DELEGATE_NAME,          # composed delegate agent
    INTERNAL_SEARCH_FLAT_NAME,              # flat-mode tool claim
    "retrieval__search_internal_knowledge", # double-underscore registry form
    "retrieval_search_internal_knowledge",  # single-underscore legacy serialization
})
```

**Flow:** any hook needing a display/LLM name calls resolve_tool_name (registry truth first; last-two-segments join only when the path is unregistered) → citations' grant gate intersects spec.tool_names with this set to decide whether an agent "has internal search".
**Invariant:** resolution must go through the registry so path-shape changes can't silently break naming; the fallback exists for paths registered AFTER resolution sites load. The vocabulary lives in ONE module because "has internal search" is a cross-hook decision (grant gating in citations.py, SSE triggers elsewhere) — each consumer importing the constant keeps resumed-conversation legacy names working without per-site drift.

### Direct test
**Probe:** exercised via citation-tracking tests (`tests/unit/agents/adapter/test_citation_tracking.py`, 22 tests). Deterministic anchors from repo root `backend/python`: `grep -c 'INTERNAL_SEARCH_TOOL_NAMES' app/agents/agent_loop/hooks/_tool_naming.py` → 2; `grep -c 'def test_' tests/unit/agents/adapter/test_citation_tracking.py` → 22.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-pipeshub-ai", query: "resolve_tool_name INTERNAL_SEARCH_TOOL_NAMES tool_naming", limit: 3, fields: ["signature", "name", "file"] });
// resolves _tool_naming.py Functions/constants line-exact
```

## Verdict
Adopt registry-first name resolution with a structural fallback and a single owned vocabulary constant for capability membership. Adapt segment-join rule and vocabulary to your registry grammar. Omit PipesHub's specific legacy spellings beyond the four-form pattern lesson.
