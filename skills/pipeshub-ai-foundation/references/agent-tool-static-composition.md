<!-- capsule-v2 -->
# AgentTool (static agent-as-tool composition, dual recursion guards)

## Source
pipeshub-ai Apache-2.0 `main@4a02110d`; Codebase Memory `pipeshub-ai`. **Question:** How does an entire AgentSpec become an ordinary callable tool — with middleware applying uniformly — and how do the two dispatch paths each prevent recursion?

## Path/Symbol
`tools/builtin/coordination/agent_tool.py` — module docstring = Layer-5 composition contract (:29–55), `MAX_AGENT_TOOL_DEPTH = 6` + `_agent_tool_depth: ContextVar[int]` (:57–59), `handle()` special-route path (:241–290), `execute()` direct path (:292–310), `_inherit_parent_skills(goal, ctx)` (:207–239).

## Signature
A REAL Tool subclass registered under any name → PRE/POST_TOOL_USE middleware (permission/approval/budget/audit) apply to calling an agent exactly as to `web_search`. Static composition (developer wires the graph ahead); spawn_agent is the dynamic-by-name counterpart.

## Data Shape
Default params `{goal, context?}`; context appended to goal text. Result of successful child run rendered by `_finalize_output`: string content (unlike spawn_agent's dict), result_note appended verbatim on success only, `[ESCALATION] {needs_input}` suffix folded in when set.

### Decisive source
```python
Two dispatch paths, two recursion guards:
- Called from inside an agent run ... the child then runs via
  run_child(parent_run_ctx=...), inheriting the caller's trace identity,
  session_id, and RunContext.spawn_depth (so MAX_SPAWN_DEPTH applies
  uniformly to static composition and dynamic spawn_agent fan-out alike).
- execute() remains for direct invocation outside any agent run. There is
  no parent RunContext to inherit depth from on that path, so cycles
  between two AgentTools are guarded by a plain ContextVar instead.
```

**Flow:** handle(): goal ← args → `_inherit_parent_skills` backfills skills the PARENT already resolved into its prompt (`scope.turn.run.extra_prompt_sections["preloaded_skills"]`) because run_child gives children a brand-new RunScope; share_parent_results ⇒ digest+staged file prepended (only place with ctx.messages) → `run_child(spec, goal, ctx.run_ctx, session_id=...)` under `stage_input_files`. execute(): depth check→set/reset around run_child(parent_run_ctx=None). result_note lives IN the tool result because instruction proximity beats system prompts in 100k-token contexts (:87–96).

**Invariant:** Depth guard differs BY PATH: inherited RunContext.spawn_depth inside runs (uniform with dynamic spawns), ContextVar outside them — a single guard would miss one path. Error results return UNTOUCHED (note governs data presentation, not errors). Skill inheritance is backfill-only: the child still runs its own preloading pass scored against ITS delegated goal.

**Probe:** `tests/unit/agent_loop_lib/tools/builtin/coordination/test_agent_tool_finalize_output.py` — plain unchanged :28, note applied :33, `[ESCALATION]` :38/:49, no-false-positive :59, apply_result_note back-compat :64. Depth guards pinned at runtime level via run-child-guards tests.

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph --project pipeshub-ai --semantic-query '["AgentTool","_inherit_parent_skills","MAX_AGENT_TOOL_DEPTH","result_note"]'
```

## Verdict
Adopt real-Tool-subclass composition (middleware uniformity), per-path recursion guarding, and result_note-in-result proximity principle; adapt skill-backfill key names.
