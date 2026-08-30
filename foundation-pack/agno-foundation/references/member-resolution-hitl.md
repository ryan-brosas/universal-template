<!-- capsule-v2 -->
# Member resolution & HITL pause — how does a nested member get found, and how does a paused child pause the whole team?

**Source:** agno Apache-2.0 `main@9644f22982ae017eaa4ad85c561d927d9ac03119`; Codebase Memory `ext-agno`. **Question:** How do you resolve a member id through sub-team nesting, and which fields must a copied requirement carry?

## _find_member_by_id / _propagate_member_pause
**Path/Symbol:** `libs/agno/agno/team/_tools.py:569` (recursive find; route variant :606) and `:643` (`_propagate_member_pause`).
**Signature:** `_find_member_by_id(team, member_id, run_context=None) -> Optional[Tuple[int, Union[Agent, Team]]]`; `_propagate_member_pause(run_response, member_agent, member_run_response) -> None`.
**Data Shape:** member ids are URL-safe strings resolved against the CURRENTLY-RESOLVED members list (callable factories already materialized); requirements are pydantic objects with optional `tool_execution`, `user_input_schema`, `member_agent_id/name/run_id` slots.

### Decisive source
```python
# recursive resolution: direct members first, then INTO sub-teams
for i, member in enumerate(resolved_members):
    if get_member_id(member) == member_id:
        return i, member
    if isinstance(member, Team):
        result = member._find_member_by_id(member_id, run_context=run_context)
        if result is not None:
            return result                      # nested hit returns the INNERMOST match + its index

# _find_member_route_by_id differs deliberately:
        if isinstance(member, Team):
            result = member._find_member_by_id(...)
            if result is not None:
                return i, member               # continue_run routes through the TOP-LEVEL sub-team

# pause propagation: copy + fill identity blanks + KEEP A LIVE HANDLE
for req in member_run_response.requirements:
    req_copy = copy(req)
    if req_copy.tool_execution is not None:  req_copy.tool_execution = deepcopy(req_copy.tool_execution)
    if req_copy.user_input_schema is not None: req_copy.user_input_schema = deepcopy(req_copy.user_input_schema)
    if req_copy.member_agent_id is None:   req_copy.member_agent_id = member_id
    if req_copy.member_agent_name is None: req_copy.member_agent_name = member_agent.name
    if req_copy.member_run_id is None:     req_copy.member_run_id = member_run_response.run_id
    req_copy._member_run_response = member_run_response   # continue_run passes it WITHOUT a DB lookup
    run_response.requirements.append(req_copy)
```

**Flow:** delegation resolves member → member runs → if response `is_paused`, propagate: shallow-copy each requirement, deep-copy mutable payload fields, stamp member identity into blank slots, attach the LIVE paused RunOutput → team loop sees unresolved requirements → `ahandle_team_run_paused` short-circuits the run.
**Invariant:** (1) Two finders exist on purpose: delegation wants the deepest executor; CONTINUE routing wants the top-level sub-team so each level's own continue machinery runs. (2) The live-handle reference (`_member_run_response`) is what makes continue-without-DB possible — dropping it forces a session lookup. (3) Identity blanks are filled only when missing — caller-stamped values win. (4) Mutable requirement fields must be deep-copied or parent and child mutate shared state.
**Probe:** graph-resolves (`search_graph "_propagate_member_pause"` → _tools.py:643-670); upstream `tests/unit/team/test_continue_run_requirements.py` + `test_paused_member_persistence.py` in executed-GREEN suite.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-agno", query: "_propagate_member_pause", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the twin-finder split and the copy-fill-blanks-keep-handle pause protocol; adapt requirement schema to your HITL types; omit agno's URL-safe-id helper. Direct tests exist (executed green).
