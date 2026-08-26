<!-- capsule-v2 -->
# StateSlot scoped state — how do modules attach per-run state without Agent growing a field per consumer?

**Source:** pipeshub-ai Apache-2.0 `main@4a02110d`; Codebase Memory `pipeshub-ai`. **Question:** What replaces both mutable Agent fields and contextvars for hierarchical agent state?

## Frozen typed handles keyed by OBJECT identity
**Path/Symbol:** `backend/python/app/agent_loop_lib/core/scope.py` — module docstring (1-32), `StateSlot` (53-97), `_PERSISTED_SLOTS` import-time registry (:99-113), `RunScope.get/set/snapshot_extensions/restore_extensions/_inherit_from` (:157-204), `TurnScope` (:223-241), `ToolScope` (:244-263).
**Signature:** `StateSlot(key: str, default_factory: Callable[[], T], inherit: bool = False, persist: bool = False)`; usage `value = scope.get(SLOT)` / `scope.set(SLOT, v)`.
**Data Shape:** Three scopes match three work units: RunScope (one per run: todos/visible_tools/turns/extra_prompt_sections/resume_turn_index + `_extensions` dict), TurnScope (per step: seen_tool_calls dup set), ToolScope (per tool call: call + tool_path/tags + messages snapshot). Scope hierarchy gives middleware uniform `ctx.scope.turn.run...` access.

### Decisive source
```python
# core/scope.py:54-67 — why not ContextVar, why frozen
"""Like contextvars.ContextVar, but scoped to one Agent.run() rather than
one asyncio Task — several agents can run sequentially on the same Task
(e.g. run_child() is awaited inline by its caller), so a ContextVar would
leak across agent boundaries in a way a per-RunScope slot does not.
Frozen (and therefore hashable): RunScope keys its extension storage by
the slot OBJECT ... two modules can never collide even if they pick the
same display name, and each slot's inherit/persist policy travels with
the slot itself — no separate registry to keep in sync."""
# :69-74 — the concurrency rule
"""Middleware reading-then-writing a slot value MUST NOT await between
the read and the write — treat slot read-modify-write as synchronous."""
```

**Flow:** module declares slot at import time → `persist=True` self-registers into `_PERSISTED_SLOTS` → checkpoint saves via `snapshot_extensions()` (JSON-safe values keyed by display name; unknown keys dropped on restore — same schema-drift policy as the rest of the checkpoint) → `run_child(parent_scope=)` copies inherit=True slots BY REFERENCE (shared mutable holders across the spawn tree are deliberate, e.g. require_critique) → consumers read through `get()` which materializes defaults lazily; there is deliberately NO `has()` (use `StateSlot[X | None]` for tri-state).
**Invariant:** ToolScope.messages is captured AFTER the assistant response lands in history — clarify's HIL_PAUSE checkpoint saves exactly this snapshot; a pre-model snapshot would resume into a dangling tool_result with no matching tool_use. TurnScope carries NO message list (different in-turn snapshots are non-interchangeable; each consumer takes its own at the right moment).
**Probe:** `tests/unit/agent_loop_lib/hooks/middleware/builtin/test_turn_guards.py` (idempotent installs :97/:118); `tests/unit/agent_loop_lib/runtime/test_run_child_streaming.py::test_run_child_seeds_context_via_public_seam` (:111); checkpoint extensions embedded at `app/agent_loop_lib/agent/observability.py:150`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pipeshub-ai", query: "StateSlot RunScope TurnScope ToolScope snapshot_extensions inherit persist", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt object-keyed frozen slots with lazy defaults, inherit-by-reference vs persist-to-checkpoint policies, and the sync-read-modify-write discipline; adapt scope field names and checkpoint schema to host; omit require_critique's shared-holder semantics unless porting that gate too. Coverage caveat: no dedicated StateSlot unit test file exists — behavior is pinned indirectly through turn-guards idempotence, spawn-slot tests, and runtime seeding tests; port with your own round-trip test for snapshot/restore.
