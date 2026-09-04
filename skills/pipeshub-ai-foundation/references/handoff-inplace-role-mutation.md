<!-- capsule-v2 -->
# handoff (in-place role mutation = horizontal ownership transfer)

## Source
pipeshub-ai Apache-2.0 `main@4a02110d`; Codebase Memory `pipeshub-ai`. **Question:** How does a run change roles mid-conversation WITHOUT spawning a child — and why is mutating the live spec safe here?

## Path/Symbol
`tools/builtin/coordination/handoff.py` — `HandoffTool.handle()` (:67–112). A2A-aligned "colleague loop": vertical (spawn_agent: new child run, waits) vs horizontal (handoff: SAME run, new owner next turn, full history carried).

## Signature
Mutates `ctx.spec` IN PLACE: `spec.name/system_prompt/description/capabilities = new_role.*`; `spec.tool_names = list(new_role.allowed_tools)` only when non-empty (:90–95).

## Data Shape
Args `{to_role, reason, note?}`. Unknown role ⇒ error result listing available names (:80–87). Result `{"handed_off_to", "reason"}`.

### Decisive source
```python
# Mutates `ctx.spec` (the SAME AgentSpec instance `agent` is
# running with — AgentSpec is a plain, non-frozen pydantic model)
# IN PLACE: since `Agent.step()` rebuilds tool_schemas/system_prompt
# from `self._spec` fresh every turn, the very next turn is served
# by the new role with no further plumbing needed.
```

**Flow:** resolve role → mutate spec fields → PROGRESSIVE DISCLOSURE merge: `agent.visible_tools |= initial_visible_tools(spec, ctx.runtime)` so the new role's essentials are immediately visible on top of what the prior role had unlocked via fetch_tools (:96–101) → write_state + timeline → next turn runs as the new role.

**Invariant:** The whole mechanism rides ONE precondition: Agent.step() must rebuild tool schemas + system prompt from the spec EVERY TURN (no caching) — that's what makes in-place mutation take effect next turn with zero plumbing. allowed_tools REPLACES only when the new role declares tools; otherwise current grants persist. visible_tools union never NARROWS mid-run.

**Probe:** No dedicated HandoffTool unit test (coverage caveat): per-turn spec rebuild + initial_visible_tools ceiling semantics pinned by tests/unit/agent_loop_lib/agent/test_max_turns_degradation.py & lazy-toolsets wiring tests; handoff referenced in spawn_scheduler/sandbox test fixtures for role-registry behavior.

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph --project pipeshub-ai --semantic-query '["HandoffTool","role_registry","initial_visible_tools"]'
```

## Verdict
Adopt horizontal-vs-vertical delegation distinction and rebuild-every-turn in-place role swap; adapt to host's spec/role registry. Requires the rebuild-per-turn invariant — do not port onto a caching loop without invalidation.
