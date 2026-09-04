<!-- capsule-v2 -->
# Citation-tracking live tool registration — how does a tool that must not exist at load time get registered and granted mid-run?

**Source:** pipeshub-ai Apache-2.0 @ `main` (drift re-entry pin `6850972`, zero production-code delta from `c28d1336`); Codebase Memory `mnt-hdd-utopia-inspo-platforms-pipeshub-ai`. **Question:** when a tool (`fetch_full_record`) can only be useful after some other tool produces record IDs, how do you register + grant it reactively without duplicate-registration races or leaking it to agents that must not call it?

## Live registration + dual-spec grant ladder
**Path/Symbol:** `backend/python/app/agents/agent_loop/hooks/citations.py:302-349` (`citation_tracking`, wired as POST_TOOL_USE by `factory.py:919`) + `_grant` (:275-299) + `ensure_fetch_full_record_available` (:352-374).
**Signature:** `citation_tracking(context, collector) -> Middleware[ToolResultContext]`; `_grant(spec, *, require_internal_search_reference: bool) -> None`.
**Data Shape:** reads `context.tool_state` dict fields `virtual_record_id_to_result` (dict) and `known_record_ids` (set); mutates `spec.tool_names: list[str]` and `run_scope.visible_tools: set[str]`.

### Decisive source
```python
async def _middleware(ctx: ToolResultContext, next_fn: "Next") -> None:
    await next_fn()
    ...
    if not collector.virtual_records and not collector.known_record_ids:
        return
    # Idempotent: two concurrent tool calls in the same gathered wave
    # can both reach this point believing the tool isn't registered
    # yet. A plain check-then-`register_tool` would raise
    # `DuplicateToolNameError` on the losing side and abort ITS OWN
    # `_grant` calls below — `register_tool_if_absent` never raises
    # for "already registered", so both sides always reach `_grant`.
    registry.register_tool_if_absent(_FetchFullRecordTool(collector, context))
    if run_scope is not None:
        _grant(run_scope.spec, require_internal_search_reference=False)
        if getattr(run_scope, "visible_tools", None) is not None:
            run_scope.visible_tools.add(_FETCH_FULL_RECORD_TOOL_NAME)
    _grant(context.root_agent_spec, require_internal_search_reference=True)
```

**Flow:** every POST_TOOL_USE → next_fn first → if EITHER proof-set non-empty → register-if-absent → grant immediate caller spec unconditionally + add to visible_tools → grant root spec ONLY if its existing grant already references an internal-search tool name.
**Invariant:** registration is never check-then-add (concurrent same-turn waves would crash the loser's grants); a mid-run registration is INVISIBLE under an explicit non-empty `spec.tool_names` grant unless appended there too (`tool_schemas_for_turn` resolves `registry.schemas(spec.tool_names)` when no toolset groups exist) — so the grant append is mandatory, not cosmetic. The root-agent grant is gated on `set(spec.tool_names) & INTERNAL_SEARCH_TOOL_NAMES` so restricted orchestrators never leak the fetch surface.

### Direct test
**Probe:** `tests/unit/agents/adapter/test_citation_tracking.py` — `grep -c 'def test_' tests/unit/agents/adapter/test_citation_tracking.py` = 22 tests incl. navigational-tools trigger classes (`TestCitationTrackingRegistersForNavigationalTools._run` :150-164). Whole adapter suite green via `/tmp/psh17venv/bin/python -m pytest tests/unit/agents/adapter/ -q` (105 passed incl. this file).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-pipeshub-ai", query: "citation_tracking register_tool_if_absent FetchFullRecordTool", limit: 5, fields: ["signature", "name", "file"] });
// resolves citations.citation_tracking Function backend/python/app/agents/agent_loop/hooks/citations.py 302-349 rank#2, registry.register_tool_if_absent Method registry.py 131-149 rank#1, plus direct tests test_citation_tracking.py
```

## Verdict
Adopt the reactive register+grant pattern for any "tool becomes callable only once data exists" need: `register_tool_if_absent` idempotency, unconditional caller grant, gated root grant keyed on an internal-search-name intersection, and visible_tools patching. Adapt the two-proof-set membership test (`virtual_records or known_record_ids`) to your own "model holds usable IDs" predicate; adapt `INTERNAL_SEARCH_TOOL_NAMES` vocabulary. Omit PipesHub naming/paths. Coverage caveat: `test_citations.py` freshness=missing in coverage metadata — read directly (it exists; 5 tests executed green).
