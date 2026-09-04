<!-- capsule-v2 -->
# Sub-agent cancellation isolation — why does a cancelled nested agent become a failed tool return instead of tearing down the caller?

**Source:** pydantic-ai MIT `main@b3cdbc96796f0294f1ac6943cdba70d14af8a0ef`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai` (full mode, coverage clean). **Question:** When a sub-agent run awaited inside a tool cancels ITSELF, how is its cancellation prevented from propagating to (or killing) the calling run?

## cancelled_sub_agent_return
**Path/Symbol:** `pydantic_ai_slim/pydantic_ai/_tool_execution.py:cancelled_sub_agent_return` (41–62), caught at `_call_tool` (:701-702: `except exceptions.RunCancelled as e: return [cancelled_sub_agent_return(call, e)], None`).
**Signature:** `cancelled_sub_agent_return(call: ToolCallPart, error: RunCancelled) -> ToolReturnPart` — content `'The sub-agent run was cancelled: {error}'`, `outcome='failed'`.
**Data Shape:** A normal failed ToolReturnPart (model-visible), NOT an exception crossing the caller's stack.

### Decisive source
```python
# _tool_execution.py:46-55 — the reasoning, in-source
# A sub-agent run awaited inside a tool cancelled *itself* (`cancel()` on its own context).
# `cancel()` cancels the run it belongs to, not the caller — and a `RunCancelled` seen inside a
# tool body is always a nested run's, since the calling run's own cancellation arrives as
# `CancelledError` and only becomes `RunCancelled` at the run's outer edge. So the caller isolates
# it: a failed tool return its model can react to, rather than tearing the whole run (or realtime
# session) down. A delegate tool that *wants* the caller cancelled too can catch `RunCancelled`
# and call `ctx.cancel()` itself; whole-tree cancellation is spelled with a shared
# `CancellationToken`.
```

**Flow:** Nested agent runs inside a tool → nested run calls its own `cancel()` → its outer edge converts `CancelledError` to `RunCancelled` → surfaces inside the tool body → `_call_tool` catches it and converts to a failed tool return part → the calling run's model sees "the sub-agent run was cancelled" and can react (retry, delegate elsewhere, finish). Caller-level cancellation still arrives as raw `CancelledError`, so the two paths never confuse each other.
**Invariant:** Cancellation identity is positional: `RunCancelled` in a tool body ⇒ belongs to a NESTED run, by construction. Whole-tree cancellation must be explicit (shared `CancellationToken`), never accidental via exception propagation. Shared deliberately by graph path and realtime session "so the two can't drift."
**Probe:** referenced upstream issue https://github.com/pydantic/pydantic-ai/issues/7199 (in-source); behavior pinned in the agent/cancellation tests (`tests/test_agent.py` grep `RunCancelled`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "cancelled_sub_agent_return RunCancelled cancel_and_drain", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the positional-cancellation identity rule and failed-return isolation for nested agents; adapt the token mechanism to your host's cancellation primitive; omit realtime-session specifics. Caveat: probe test located via grep only (not full-file read this pass) — noted as best-effort.
