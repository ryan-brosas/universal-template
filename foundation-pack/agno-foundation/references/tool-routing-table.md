<!-- capsule-v2 -->
# Tool-routing table — how does one function assemble the leader's toolset, and why do duplicate names silently lose?

**Source:** agno Apache-2.0 `main@9644f22982ae017eaa4ad85c561d927d9ac03119`; Codebase Memory `ext-agno`. **Question:** What is the precedence order of built-in vs user tools, and what is the collision policy?

## _determine_tools_for_model
**Path/Symbol:** `libs/agno/agno/team/_tools.py:114` (body :114-501; Team wrapper delegates via `Team._determine_tools_for_model` team.py:1385-1429).
**Signature:** `_determine_tools_for_model(team, model, run_response, run_context, team_run_context, session, ..., async_mode=False, learning_tools=None) -> List[Union[Function, dict]]`.
**Data Shape:** input tools may be Toolkit | Callable | Function | raw dict (provider-builtin); output is normalized `Function` objects with `_team`, `_run_context`, joint media fields injected; strict-mode flag decided once from run_context.output_schema.

### Decisive source
```python
# assembly order (fixed):
resolved_tools = get_resolved_tools(team, run_context)          # 1 user tools first
if run_context.client_tools: resolved_tools += client_tools     #    + AG-UI frontend tools
# 2 flag-gated built-ins appended after:
read_chat_history → chat-history tool; enable_agentic_memory → update_user_memory;
enable_agentic_state → update_session_state; search_past_sessions → search+read pair;
knowledge+search_knowledge → knowledge_search; update_knowledge → add_to_knowledge
if team.mode == TeamMode.tasks:
    _tools.extend(_get_task_management_tools(...))              # 3a tasks mode: task tools INSTEAD
elif resolved_members:
    _tools.append(delegate_task_func)                           # 3b coordinate mode: delegation tool
                                                                #    (+ member_information)
# collision policy inside the normalization loop:
for name, _func in toolkit_functions.items():
    if name in _function_names:
        log_warning(f"Duplicate tool name '{name}' ... skipping the duplicate.")
        continue                                                # FIRST WINS — later silently dropped
_function_names.append(name)
```
Post-pass: every Function gets `process_entrypoint(strict=effective_strict)` (per-tool explicit strict overrides the global), `team.tool_hooks` attached; media collection runs ONLY if some function signature mentions images/videos/audios/files (:481-499); MCP tools skipped when `check_mcp_tools` set and not initialized.

**Flow:** resolve callable factories → collect user tools → append flag-gated built-ins → append mode-exclusive delegation OR task tools → normalize each entry to Function with dedupe-by-name (first wins) → strict/hooks/media injection.
**Invariant:** (1) Tasks mode and delegation tool are MUTUALLY EXCLUSIVE — a porter wiring both gives the leader two ways to delegate and ambiguous routing. (2) Duplicate names keep the FIRST registration and drop the rest WITH ONLY A WARNING — the documented `update_user_memory` trap (team.py:302-306): MemoryManager and LearningMachine both register that name and "the learning store's tool is dropped without a word". (3) Raw dicts pass through untouched (provider-executed). (4) Media collection is gated on actual parameter needs, not unconditional.
**Probe:** graph-resolves (`search_graph "_get_task_management_tools"` → _task_tools.py:92-1182; wrapper at team.py:1385-1429); duplicate-policy exercised by upstream suites under `tests/unit/team/` executed GREEN.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-agno", query: "team._tools._determine_tools_for_model", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the fixed assembly order and first-wins dedupe; adapt the flag list to your feature set; omit agno's specific toolkit-instruction memoization. Caveat: first-wins means tool REGISTRATION order is behavior — document it wherever tools are composed.
