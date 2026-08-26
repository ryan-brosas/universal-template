<!-- capsule-v2 -->
# History-seeded PRE_TURN hooks — how do follow-up requests inherit the previous turn's tools, artifacts, and results without re-fetching?

**Source:** pipeshub-ai Apache-2.0 @ `main` (pin `6850972`); Codebase Memory `mnt-hdd-utopia-inspo-platforms-pipeshub-ai`. **Question:** a fresh Agent/RunScope per HTTP request forgets everything — where is the earliest point hooks can restore cross-request context, and what does each restorer contribute?

## Four PRE_TURN restorers over one bounded transcript
**Path/Symbol:** `backend/python/app/agents/agent_loop/hooks/memory.py` — `conversation_enrichment` :36-53 + `seed_visible_tools_from_history` :76-127; `backend/python/app/agents/agent_loop/hooks/artifact_context.py` — `artifact_context_reminder` :54-102; wiring order `factory.py:926-929`.
**Signature:** all `(context: AgentContext) -> Middleware[TurnContext]`, gated on `ctx.turn_index != 0` (history is fixed for the run; nothing new can appear later).
**Data Shape:** reads `previous_conversations` turns with `role=="bot_response"` carrying `tool_results[]` entries (`tool_name`, `artifact_id`, `args`, `result_summary`); writes `run_scope.visible_tools` and `goal.constraints`.

### Decisive source
```python
# seed_visible_tools_from_history — why it MUST be a PRE_TURN hook:
# Must run as a PRE_TURN hook, not in `factory.create()` directly:
# `Agent.visible_tools`'s setter is backed by `RunScope`, which
# `Agent.run()` only constructs once the run actually starts (see
# `core/scope.py`) — `factory.create()` returns before that, so setting
# it there would silently no-op. PRE_TURN dispatches AFTER `RunScope`
# exists but BEFORE `tool_schemas_for_turn()` reads/lazily-initializes
# `agent.visible_tools`
...
prior_names &= registered            # drop names that no longer resolve
if spec.tool_names:
    prior_names &= set(spec.tool_names)   # respect the current grant
run_scope.visible_tools = initial_visible_tools(spec, run_scope.runtime) | prior_names
```

**Flow:** conversation_enrichment detects short follow-ups ("yes", "do it") via ConversationMemory and appends a reuse-don't-recall reminder → attachment_rehydration refills citation maps (own capsule) → artifact_context_reminder lists VISIBLE artifacts (STAGING code artifacts excluded so they never crowd out deliverables; limit 20) enriched with args/summaries cross-referenced from transcript tool_results → seed_visible_tools unions essentials/pinned with history-used tool names.
**Invariant:** Goal.constraints is the ONE run-scoped object a hook can mutate that the prompt builder reads back. Visible-tool seeding must intersect with registered names AND the spec grant (stale references degrade to absent, never error). Registry queries are fail-open (warn + next_fn). The visible_tools setter silently no-ops before RunScope exists — timing IS the contract.

### Direct test
**Probe:** `tests/unit/agents/adapter/test_hooks.py::test_appends_reminder_for_follow_up_query` :209, `.test_only_fires_on_first_turn` :226; `tests/unit/agents/adapter/test_artifact_context.py::test_includes_args_and_summary_from_conversation` :61, `.test_registry_failure_does_not_raise` :155. Execute: `/tmp/psh17venv/bin/python -m pytest tests/unit/agents/adapter/test_hooks.py tests/unit/agents/adapter/test_artifact_context.py -q` (23 passed at pin).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-pipeshub-ai", query: "seed_visible_tools_from_history conversation_enrichment previous_conversations", limit: 4, fields: ["signature", "name", "file"] });
// resolves hooks/memory.py symbol cluster line-exact
```

## Verdict
Adopt the PRE_TURN-restorer family pattern for per-request agent builds: one bounded transcript, four orthogonal restorers (results-reuse nudge, attachments, artifacts, tool visibility), turn-0-only gating, constraints as the model-facing channel. Adapt detection heuristics and limits. Omit PipesHub transcript serialization specifics.
