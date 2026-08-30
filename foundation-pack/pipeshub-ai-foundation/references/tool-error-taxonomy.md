<!-- capsule-v2 -->
# Tool error taxonomy — what exception hierarchy do path-based registries need so broad catches keep working?

**Source:** pipeshub-ai Apache-2.0 `main@4a02110dd9a7a644d8ba7a5ccd295c58a3c3628f`; Codebase Memory `pipeshub-ai`. **Question:** How do you extend an error hierarchy (specific duplicates, path-mismatch, denial) WITHOUT breaking existing `except ToolError` call sites?

## Alias-not-subclass merge + name-vs-path uniqueness split
**Path/Symbol:** `backend/python/app/agent_loop_lib/tools/errors.py:ToolValidationError/ToolNotFoundError/DuplicateToolPathError/DuplicateToolNameError/ToolPathMismatchError/InvalidToolPathError/ToolDeniedError/UnknownHookEventError` (L28–104); base at `core/exceptions.py` (`AgentLoopError/RegistryError/ToolError`).
**Signature:** Each carries structured fields (`path`, `name`, `tool_path`+`expected_prefix`+`tool_name`, `reason`, `event`+`known_events`) alongside the message — catch sites can branch on data without string parsing.
**Data Shape:** `AgentOSError = AgentLoopError` is an ALIAS, not a subclass.

### Decisive source
```python
# Alias rather than a new base class: every tool/middleware/hook error IS an
# AgentLoopError, so `except AgentLoopError` (already used at several call
# sites) keeps catching them without change.
AgentOSError = AgentLoopError

class DuplicateToolNameError(ToolError):
    """Short names must stay globally unique because they are what the LLM's
    function-calling interface addresses (`ToolCall.name`); paths are for
    middleware routing, not model-facing addressing."""

class ToolPathMismatchError(ToolError):
    """Raised when a tool's path is inconsistent with its owning toolset's
    path_prefix."""
```

**Flow:** registration-time validation raises `InvalidToolPathError` (grammar `/segment/segment/`) / `DuplicateToolPathError` / `DuplicateToolNameError` / `ToolPathMismatchError`; resolution failure raises `ToolNotFoundError(path)`; argument validation raises `ToolValidationError`; strict opt-in callers may convert denials into `ToolDeniedError` instead of a failed ToolResult; hook registry rejects unknown events with a self-describing message listing known events and how to register one.
**Invariant:** (1) New specificity rides EXISTING bases — merging via alias keeps every historical catch site valid; forking a parallel hierarchy would silently narrow old handlers. (2) Name uniqueness and path uniqueness are SEPARATE invariants with separate exceptions: names are the model-facing address space, paths the middleware address space. (3) Errors-as-data still rules the hot path (failed ToolResults); exceptions are for registry/infra programming errors and explicit opt-ins.
**Probe:** `tests/unit/agent_loop_lib/tools/test_registry.py:178–188` (duplicate short-name registration expects `DuplicateToolNameError`), :264 (original-wins path does NOT raise); `tests/unit/agent_loop_lib/tools/test_executor_validation_feedback.py` + `tests/unit/control_plane/test_control_plane_coverage.py` exercise `ToolValidationError`. `ToolPathMismatchError` has no direct test at HEAD — caveat recorded.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pipeshub-ai", query: "DuplicateToolNameError ToolNotFoundError InvalidToolPathError ToolDeniedError UnknownHookEventError", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the taxonomy split (name vs path addressing) + alias-merge discipline when extending any error hierarchy under compatibility constraints; adapt wording/fields. Omit nothing portable here — it's small by design. Coverage caveat: path-mismatch branch untested upstream; duplicate/validation branches pinned.
