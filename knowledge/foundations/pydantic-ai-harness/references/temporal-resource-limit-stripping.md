<!-- capsule-v2 -->
# Temporal-aware resource limits: strip elapsed-time caps under workflow replay, keep memory caps

## Source / Question
`pydantic_ai_harness/code_mode/_toolset.py` — `_resolve_resource_limits` (:239–258) + `_in_temporal_workflow` (:90+) @ `main@76db3dec` (#621 "keep Temporal subclass replays timing-safe"; Codebase Memory `pydantic-ai-harness`) — Sandbox snippets run with a wall-clock duration cap, but inside a Temporal workflow the code is REPLAYED deterministically: an elapsed-time check can make the original execution and its replay take different branches, which Temporal cannot record. How do you keep resource backstops without breaking replay determinism?

> PASS-9 CLOSURE-HOLD ADJUDICATION ([DONE:461], dedicated lane drain-lane-pydantic-ai-frameworks): the standing conditional "dynamic_workflow/_toolset.py `_resolve_resource_limits` twin" resolves as a DELIBERATE DIVERGENCE, not a missed port. The twin (`dynamic_workflow/_toolset.py:93-108`) takes NO `in_temporal_workflow` flag and never strips duration — because the DynamicWorkflow plane has no elapsed-time cap to begin with: `DynamicWorkflow.resource_limits` defaults to a 256 MB memory backstop with NO `max_duration_secs` (`_capability.py` :103-110: "There is no default `max_duration_secs`: Monty's timer bounds in-sandbox execution time and time awaiting sub-agents does not count against it"), so replay determinism is preserved STRUCTURALLY rather than by detection-and-strip. Porters choose ONE policy: (a) code_mode's detect-and-strip (richer default limits, framework owns replay safety), or (b) dynamic_workflow's no-timing-by-default (simpler resolver; explicit user-set caps are their own replay risk). Both tests below re-executed GREEN 2 passed in `/tmp/harness-p6-venv` at `76db3dec` — supersedes the earlier no-runner caveat.

## Path / Symbol
`code_mode/_toolset.py` — `_resolve_resource_limits(limits, *, in_temporal_workflow=False)` (:239–258), `_in_temporal_workflow(ctx)` (:90+; `runtime_checkable` protocol walking `ctx.capabilities` MROs for `pydantic_ai.durable_exec.temporal` modules + duck-typed `in_durable_context`, dodging the optional extra import), consumption at session creation :866; validation-only path WITHOUT the flag at :600.

## Signature
```python
def _resolve_resource_limits(limits, *, in_temporal_workflow: bool = False) -> ResourceLimits:
    if limits == 'unlimited': return {}
    # unknown-key validation against CodeModeResourceLimits annotations → UserError
    max_duration_secs = 30 if limits is None else limits.get('max_duration_secs', 30)
    max_memory = 256 * 1024 * 1024 if limits is None else limits.get('max_memory', 256*1024*1024)
    if in_temporal_workflow:
        # An elapsed timer may make the original run and replay take different branches,
        # which Temporal cannot record.
        max_duration_secs = None
    return {'max_duration_secs': max_duration_secs, 'max_memory': max_memory}
```

## Data Shape
Defaults are BACKSTOPS applied when the caller passed nothing (30s / 256MiB); `'unlimited'` short-circuits to `{}`; unknown dict keys raise `UserError` naming valid keys. Duration is per-snippet in practice: Monty enforces per SESSION, and consecutive `run_code` calls share one session, so consecutive snippets share one allowance and anything that resets the session starts fresh (`CodeModeResourceLimits` docstring :230–233).

### Decisive source
The asymmetry is the contract: under `in_temporal_workflow` ONLY `max_duration_secs` is nulled (:254–257) — memory stays capped because allocation is deterministic to record. Detection is duck-typed via capability MROs so the durable-exec extra stays optional. Tests: `tests/code_mode/test_code_mode.py::test_temporal_disables_elapsed_time_limits` (:836) and `test_temporal_subclass_disables_duration_but_keeps_memory_limit` (:860) — the subclass test pins that a Temporal-derived capability keeps the memory limit while dropping duration.

**Flow:** enter toolset → detect Temporal context from capabilities → resolve limits (duration stripped iff in-workflow) → create/reuse REPL session with those limits → exhaustion classified by the marker table (see sandbox-limit markers capsule) where the STRICT classifier alone advises restart.
**Invariant:** never enforce elapsed time on code that will be deterministically replayed; memory/other deterministic resources remain enforced; unknown limit keys fail loudly at entry.
**Coverage caveat:** probes pinned to the upstream suite; not executed live this pass (no montpy/pydantic-ai env in the inspo clone) — assertions cited from source. (SUPERSEDED pass 9: both temporal tests now EXECUTED GREEN in /tmp/harness-p6-venv, see adjudication above.)

## Probe (direct test)
`tests/code_mode/test_code_mode.py::test_temporal_disables_elapsed_time_limits` :836, `::test_temporal_subclass_disables_duration_but_keeps_memory_limit` :860.

## Retrieve
```
codebase-memory-mcp cli search_graph --project pydantic-ai-harness --name-pattern '_resolve_resource_limits|in_temporal_workflow|max_duration' --detail ids
```

## Verdict
Adopt the strip-timing-keep-determinism rule for ANY replay-based durable executor (Temporal, DBOS, Restate). Adapt detection to your framework's context marker. Omit the marker-table/restart-guidance machinery if you have no sandbox exhaustion UX (covered separately).
