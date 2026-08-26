<!-- capsule-v2 -->
# Best-of-N judged fan-out — how do you pick one winner from N parallel child runs without a broken judge failing the call?

**Source:** pipeshub-ai Apache-2.0 `main@4a02110d`; Codebase Memory `pipeshub-ai`. **Question:** How does run-level best-of-N execute N candidates concurrently, and what exactly happens when the judge LLM errors, returns garbage, or every candidate fails?

## Parallel candidates via run_child + judge that degrades, never raises
**Path/Symbol:** `backend/python/app/agent_loop_lib/agent/best_of_n.py` — `run_best_of_n` (:94-161), `_judge` (:44-91), `_run_one_candidate` (:34-41); dispatched by the `best_of_n` special route in `tools/builtin/coordination/best_of_n.py`.
**Signature:** `async def _judge(agent, candidate_goal_desc, criteria, successful: list[tuple[int, AgentResult]]) -> tuple[int, str]` — the int is an index into **`successful`, not into `candidates`**; `async def run_best_of_n(agent, call: ToolCall, goal, turn_index, started_at) -> ToolResult`.
**Data Shape:** Args clamped to `n = max(2, min(int(args.get("n", 2)), 5))`. Candidate spec = `runtime.spec_for_role(role, **overrides)` where overrides only include keys explicitly present (`tools` → `tool_names`, `model`). Candidates run through `AgentRuntime.run_child()` — the SAME child primitive as spawn_agent/agent_as_tool, so depth guards, spec scoping, cancellation propagation apply unchanged. Result content is `{output, n, winner_index, judge_reason}`.

### Decisive source
```python
team_id = str(uuid.uuid4())
candidates = await asyncio.gather(*(
    _run_one_candidate(agent, candidate_spec, candidate_goal, team_id) for _ in range(n)
))
successful = [(i, c) for i, c in enumerate(candidates) if c.success]   # original indices kept

# _run_one_candidate: ANY exception becomes a failed AgentResult (never propagates)
except Exception as e:
    return AgentResult(goal=candidate_goal, success=False, error=str(e))

# _judge degradation ladder — every failure mode returns index 0 with a reason:
if len(successful) == 1:                       return 0, "Only one successful candidate — judge skipped."
if agent.runtime.transport_registry is None:   return 0, "No model available for judging; ..."
except StructuredSingleShotError as exc:       return 0, f"Judge call failed ({exc}); ..."
local_index = max(0, min(int(verdict.get("winner_index", 0)), len(successful) - 1))

winner_index = successful[local_index][0]      # local -> ORIGINAL candidate mapping
```

**Flow:** clamp n → resolve role spec (+optional tool/model overrides) → observe state/timeline → gather all N via `asyncio.gather` on one shared `team_id` → filter successes KEEPING their original indices → if none survived, error `ToolResult` listing every candidate's error → else judge (single structured single-shot over candidates' final outputs, strict-criteria system prompt) → map local winner back to the original candidate → verdict timeline event → success result. The caller wraps `_judge` in a second `try/except` so even an unexpected exception escaping it degrades to first-successful instead of failing the whole tool call.
**Invariant:** (1) A broken judge must NEVER fail an otherwise-successful best-of-N — every judge failure path falls back to the first successful candidate WITH a human-readable reason string in the payload. (2) Judge indices are LOCAL to the successful list; mapping through failed candidates is explicit (`successful[local_index][0]`) — indexing `candidates[local_index]` directly is THE wrong port. (3) Out-of-range/missing `winner_index` values are clamped/defaulted, never trusted. (4) All-fail is an ERROR result (is_error=True), not a silent empty.
**Probe:** `backend/python/tests/unit/agent_loop_lib/agent/test_best_of_n.py` — `test_winner_index_maps_through_failed_candidates` (:140, local-vs-original divergence), `test_judge_structured_error_falls_back_to_first_successful` (:104), `test_judge_generic_exception_is_caught_by_caller` (:121), `test_all_candidates_fail_returns_error_result` (:164), `test_n_is_clamped_between_two_and_five` (:182).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pipeshub-ai", query: "run_best_of_n _judge best-of-n candidates", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the gather-with-shared-team-id fan-out reusing the standard child-launch primitive, the keep-original-indices successful list, and the total judge-degradation ladder (single candidate / no transport / structured error / unexpected exception → first-successful with reason); adapt n bounds, judge prompt, and result payload shape to host; omit the obs timeline events if the host has no timeline surface. Direct-test coverage is strong (16 scripted tests).
