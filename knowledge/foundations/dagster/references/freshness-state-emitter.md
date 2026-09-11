<!-- capsule-v2 -->
# Freshness daemon — how are per-asset freshness states computed and change events emitted?

**Source:** Dagster Apache-2.0 `master@4344eb7f4cf588c801c17489228790f002276aca`; Codebase Memory `ext-dagster`. **Question:** How does a scheduler-side daemon turn per-asset policies into state-change events without N+1 query storms?

## Gather-then-fan-out evaluation with policy-type dispatch
**Path/Symbol:** `python_modules/dagster/dagster/_daemon/freshness.py:FreshnessDaemon` (whole file, 112 lines; `run_iteration` :32-50, `_evaluate_assets` :52-68, `_evaluate_asset` :90-112).
**Signature:** `class FreshnessDaemon(IntervalDaemon)` with `_INTERVAL_SECONDS = int(os.environ.get("FRESHNESS_DAEMON_INTERVAL_SECONDS", "30"))`.
**Data Shape:** Policy lookup: `node.freshness_policy_or_from_metadata` (1.11+ first-class property; pre-1.11 metadata fallback — both supported). Evaluator registry: `FRESHNESS_EVALUATORS_BY_POLICY_TYPE` keyed by policy class. Output: `FreshnessStateChange(key, previous_state, new_state, state_change_timestamp)` runless asset event.

### Decisive source
```python
coroutines = [
    self._evaluate_asset(context=loading_context, node=node)
    for node in asset_graph.asset_nodes
]
return await asyncio.gather(*coroutines)
...
previous_state = await FreshnessStateRecord.gen(context, node.key)
current_state = await self._compute_asset_freshness_state(context=context, node=node)
if previous_state is None or previous_state.freshness_state != current_state:
    # Note: future refactors could batch the event emission given a new instance method, but
    # freshness state change events are somewhat rare so batching would not improve performance
    context.instance._report_runless_asset_event(  # noqa: SLF001
        asset_event=FreshnessStateChange(...)
    )
    return True
return False
```

**Flow:** every 30s (interval-daemon) → build ONE loading context shared by all assets ("create a loading context to batch queries against") → gather per-asset coroutines → unknown policy class ⇒ warn + `FreshnessState.UNKNOWN` (never crash); no policy ⇒ NOT_APPLICABLE → diff against previous record; emit ONLY on transition. Daemon type string `FRESHNESS_DAEMON`.
**Invariant:** Events are edge-triggered (state CHANGED), not level-triggered — downstream alerting would spam otherwise; batching of reads is fine but emission stays per-event by design (documented rarity). The daemon is read-only over user code: it never launches runs.
**Probe:** `python_modules/dagster/dagster_tests/daemon_tests/test_freshness_daemon.py`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-dagster", query: "FreshnessDaemon evaluate_freshness FreshnessStateRecord FreshnessStateChange", limit: 10 });
```

## Verdict
Adopt batch-context + edge-triggered emission + unknown-policy tolerance; adapt policy classes/evaluators to your domain; omit the pre-1.11 metadata fallback if you control schema evolution end-to-end. Pinned by a dedicated upstream test file.
