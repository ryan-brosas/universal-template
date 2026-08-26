<!-- capsule-v2 -->
# Approval bridge — how does a one-question port ("may this call proceed?") reuse a rich legacy approval system without replacing it?

**Source:** pipeshub-ai Apache-2.0 `main@4a02110dd9a7a644d8ba7a5ccd295c58a3c3628f`; Codebase Memory `pipeshub-ai`. **Question:** Where do you cut the seam between the new tool pipeline and an existing RiskLevel/ApprovalPolicy/HIL apparatus?

## StorageBackedApprovalHandler delegates to ApprovalHook.check; require_approval denies with the FULL tool path; denial stamps decision id in ctx.metadata
**Path/Symbol:** `backend/python/app/agent_loop_lib/tools/approval.py:ApprovalHandler/StorageBackedApprovalHandler/require_approval` (L27–66); wrapped legacy system `modules/stores/approval/hook.py:ApprovalHook`; registration `control_plane.py` (`hooks=["approval"]`).
**Signature:** `Protocol.request_approval(ctx: ToolCallContext) -> bool`; `StorageBackedApprovalHandler(approval_hook: ApprovalHook)`; `require_approval(handler)` → async `(ctx, next_fn)` middleware.
**Data Shape:** Reconstructs a legacy `ToolCall(id=str(ctx.tool_use_id), name=<last path segment>, arguments=dict(ctx.tool_input))` per call; on denial writes `ctx.metadata["approval_decision_id"] = decision.decision_id` before returning False.

### Decisive source
```python
# The module docstring states the migration stance:
"""The new tool pipeline only needs one thing from approval: "is this call
allowed to proceed?" (request_approval(ctx) -> bool). Everything else —
RiskLevel lookup, ApprovalPolicy resolution, session-scoped decision
caching, HIL submission — already exists and works ... this module bridges
the two rather than replacing the richer system with the simpler port."""

async def request_approval(self, ctx):
    name = ctx.tool_path.rsplit("/", 1)[-1]     # last segment IS the legacy name
    call = ToolCall(id=str(ctx.tool_use_id), name=name, arguments=dict(ctx.tool_input))
    decision = await self._hook.check(call, session_id=ctx.session_id)
    if not decision.approved:
        ctx.metadata["approval_decision_id"] = decision.decision_id  # audit handle
    return decision.approved
```

**Flow:** PRE_TOOL_USE (when `approval` in hooks) → require_approval asks the handler → approved: next() runs, decision stays allow → denied: `ctx.deny('tool call to <path> was not approved')`, next never called, decision id preserved in metadata for downstream correlation/audit.
**Invariant:** (1) Bridge, don't replace: the simple port answers ONE question; policy resolution/risk/caching/HIL stay owned by the existing hook. (2) The handler derives the legacy tool NAME as the last path segment — passing the full path would miss every legacy policy keyed by method names. (3) Denials must carry a durable correlation handle (decision_id) at DENIAL TIME, not via post-hoc lookups. (4) Protocol is runtime_checkable so hosts plug any storage-backed or human-approval backend.
**Probe:** `tests/unit/agent_loop_lib/tools/test_approval.py` — :40 approved leaves metadata untouched, :53 denial returns False AND stamps decision id, :66 name-is-last-path-segment, :83 protocol conformance, :92–117 middleware ladder (approved→next+allow; denied→no-next+deny-with-path; handler receives the context).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pipeshub-ai", query: "require_approval StorageBackedApprovalHandler ApprovalHook request_approval", limit: 8, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the minimal-port-over-rich-system bridge + last-segment name derivation + denial-time metadata stamping when modernizing any governed execution pipeline. Adapt ToolCall shape to host legacy API. Omit nothing portable. No coverage caveat.
