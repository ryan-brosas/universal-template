<!-- capsule-v2 -->
# Supervisor run spine — how does a Team leader loop survive retries, cancellations, and background-task leaks?

**Source:** agno Apache-2.0 `main@9644f22982ae017eaa4ad85c561d927d9ac03119`; Codebase Memory `ext-agno`. **Question:** What is the exact ordered contract of the async team-leader run spine, and which failure classes bypass the retry loop?

## Async leader spine `_arun`
**Path/Symbol:** `libs/agno/agno/team/_run.py:2956` (`async def _arun`, body :3023–3360).
**Signature:** `async def _arun(team, run_response: TeamRunOutput, run_context: RunContext, session_id: str, user_id=None, response_format=None, ..., **kwargs) -> TeamRunOutput`.
**Data Shape:** mutates `run_response` in place (status/events/content/metrics); reads `team.retries/delay_between_retries/exponential_backoff`; returns the same object on every path — never raises outward except re-raised `asyncio.CancelledError` (client disconnect).

### Decisive source
```python
num_attempts = team.retries + 1
for attempt in range(num_attempts):
    ...
    try:
        await araise_if_cancelled(run_response.run_id)
        # 1 pre-hooks → 2 resolve factories+tools → 3 messages → 4 memory/learning bg tasks
        # 5 reasoning → 6 acall_model_with_fallback → output/parser models
        # 7 _update_run_response → 7b HITL pause short-circuit → 8 media → 9 structured
        # 10 post-hooks → 11 await_for_open_threads + metric merge → 12 summary/followups
        run_response.status = RunStatus.completed
        await _acleanup_and_store(...)
        return run_response
    except RunCancelledException as e:
        run_response = _handle_team_run_cancellation(run_response, e, run_messages, session=team_session)
        if run_response.run_id:
            await adrain_member_tasks(run_response.run_id)   # bounded 5s drain BEFORE persist
        ...return run_response
    except (InputCheckError, OutputCheckError) as e:        # guardrail failures NEVER retry
        ...return run_response
    except (KeyboardInterrupt, asyncio.CancelledError) as cancel_exc:
        if isinstance(cancel_exc, asyncio.CancelledError):
            _persist_cancelled_team_run_in_background(...)  # detached task: cancel scope would abort an inline write
        else:
            await _acleanup_and_store(...)                  # Ctrl-C: inline persist before loop exit
        if isinstance(cancel_exc, asyncio.CancelledError): raise
        return run_response
    except Exception as e:
        if attempt < num_attempts - 1:
            delay = team.delay_between_retries * (2**attempt) if team.exponential_backoff else team.delay_between_retries
            await asyncio.sleep(delay); continue
        ...return run_response
finally:
    _disconnect_connectable_tools(team); await _disconnect_mcp_tools(team)
    for t in (memory_task, learning_task):                  # cancel + await so warnings never leak
        if t is not None and not t.done(): t.cancel(); try: await t
        except asyncio.CancelledError: pass
    await acleanup_run(run_response.run_id)                 # ALWAYS drop cancel-tracking entry
```

**Flow:** register-for-cancel → session setup → retry-loop{cancel-check → pre-hooks → factory/MCP refresh → tool determination → messages → spawn memory/learning background tasks → reasoning → model-with-fallback → HITL-pause check → post-hooks → join background tasks → summary → completed} → cleanup/store; every failure class has a dedicated handler; `finally` disconnects tools, cancels un-joined background tasks, and de-registers the run.
**Invariant:** (1) `RunCancelledException`/guardrail errors are terminal — they consume NO retry attempt; only bare `Exception` retries. (2) `run_messages` is bound `None` BEFORE the try so the cancellation handler can read it via `locals().get("run_messages")` even when cancel fires pre-build (:3046-3048 comment). (3) CancelledError persists via detached task because the closing cancel scope would abort an inline DB write; Ctrl-C persists inline because a detached task would not run before `asyncio.run` exits. (4) The `finally` block always deregisters the run id — a leaked registry entry would make the NEXT run with a recycled id instantly "cancelled".
**Probe:** `tests/integration/teams/test_team_run_cancellation.py` (12 tests: content preservation, event persistence, non-streaming sync/async, member-run-in-output on cancel, continue-after-cancel); upstream suite executed GREEN 94 passed at pin (`tests/unit/team` subset incl. `test_team_run_regressions.py`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-agno", query: "Team.arun retry loop", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the ordered 13-step spine, the failure-class handler split (retry vs terminal), and the dual-path persist-on-cancel; adapt handler names/session types to your host; omit agno's specific telemetry/logging calls. Caveat: streaming twins `_arun_stream` (:3582+) mirror this ordering but add event-fan-out concerns not covered here.
