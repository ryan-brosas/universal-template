<!-- capsule-v2 -->
# Delegation message bus — how does a leader's delegate tool stream member events while staying cancellable mid-flight?

**Source:** agno Apache-2.0 `main@9644f22982ae017eaa4ad85c561d927d9ac03119`; Codebase Memory `ext-agno`. **Question:** How do member-run events reach the caller's stream, and what happens to the member when the team is cancelled during delegation?

## Delegate tool (sync + async twins)
**Path/Symbol:** `libs/agno/agno/team/_default_tools.py:441` (`_get_delegate_task_function` factory; streaming loop :657-689 sync / :843-876 async).
**Signature:** `delegate_task_to_member(member_id: str, task: str) -> Iterator[RunOutputEvent | TeamRunOutputEvent | str]` (async twin `adelegate_task_to_member`); registered as the ONLY delegation tool in coordinate mode (`_determine_tools_for_model`, _tools.py:303-324) — tasks mode swaps it for the `_task_tools` family instead.
**Data Shape:** yields member events with `parent_run_id` stamped; final member output is captured, not yielded; returns a plain string result to the leader model; terminal event classes whitelisted in `_MEMBER_TERMINAL_EVENT_TYPES` (:91-98).

### Decisive source
```python
draining_after_cancel = False
async for ev in member_agent_run_response_stream:
    if isinstance(ev, (TeamRunOutput, RunOutput)):
        member_agent_run_response = ev; continue        # capture final object, never yield
    if isinstance(ev, _MEMBER_TERMINAL_EVENT_TYPES):
        ev.parent_run_id = ev.parent_run_id or run_response.run_id
        yield ev                                        # forwarded EVEN while draining
        if ev.is_cancelled: draining_after_cancel = True
        continue
    if draining_after_cancel:
        continue                                        # swallow ordinary events post-cancel
    ev.parent_run_id = ev.parent_run_id or run_response.run_id
    yield ev
    try:
        await araise_if_cancelled(run_response.run_id)  # per-event cancel poll
    except RunCancelledException:
        if member_run_id:
            await _acascading_cancel_run(member_run_id) # cascade into the child
        draining_after_cancel = True
        continue                                        # keep draining so AsyncIterator exits PROPERLY
if draining_after_cancel:
    raise RunCancelledException("")                     # re-arm team-level handler
```
Pre-loop registration: `await aregister_member_run(team_run_id, member_run_id)` (:819/:880); the async tool registers its own `asyncio.current_task()` in the drain bucket FIRST (:796-798) so a cancel that lands mid-delegation can be awaited before persistence.

**Flow:** find member recursively → initialize member + copy session_state per delegation → run member (same session_id!) → classify each event: final-output captured / terminal forwarded always / ordinary suppressed after cancel → per-event cancel check cascades into the child → post-processing stamps `parent_run_id`, upserts member run into team session, merges state copy back.
**Invariant:** (1) NEVER break out of the member stream — the comment says it verbatim ("Do NOT break out of the loop, AsyncIterator need to exit properly"); drain instead. (2) Terminal events are forwarded even while draining so the caller's transcript keeps its completed/cancelled/error markers. (3) Member session_state is copy-on-delegate, merge-on-return (`merge_dictionaries`) — members cannot mutate shared state concurrently. (4) Members share the TEAM's session_id; only the parent_run_id distinguishes them.
**Probe:** `tests/unit/team/test_delegate_closure_bug.py` (closure-capture regressions for the fan-out variant, executed GREEN); integration `test_team_run_cancellation.py::test_member_run_in_team_run_output_on_cancellation_{sync,async}`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-agno", query: "delegate_task_to_member register_member_run", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the event-classification trio and drain-don't-break rule; adapt event type names to your bus; omit agno's logger switching (use_agent_logger/use_team_logger). Caveat: BM25 search_graph does not resolve `adelegate_task_to_member`/`execute_tasks_parallel` directly (closure-scoped names) — retrieve via the factory symbol or file Module node.
