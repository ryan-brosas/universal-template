<!-- capsule-v2 -->
# Automation sensor ownership & eligibility — how do DA sensors partition asset coverage so nothing double-launches?

**Source:** Dagster Apache-2.0 `master@4344eb7f4cf588c801c17489228790f002276aca`; Codebase Memory `ext-dagster`. **Question:** When multiple automation-condition sensors cover overlapping assets across code locations, what stops duplicate materializations?

## Origin-scoped eligible keys + metadata-claimed job keys
**Path/Symbol:** `python_modules/dagster/dagster/_daemon/asset_daemon.py:_async_process_auto_materialize_tick` eligibility block (lines 897-945) + `_sensor_is_enabled` (:1516-1527).
**Signature:** inline set computation over `(sensor, repository)` pairs; `auto_materialize_entity_keys: set[EntityKey]`.
**Data Shape:** Inputs: sensor's `asset_selection` resolved against ONLY its own repo graph; workspace-wide `RemoteWorkspaceAssetGraph` for origin checks; `EMIT_BACKFILLS_METADATA_KEY` sensor metadata claims job keys.

### Decisive source
```python
# Ensure that if there are two identical asset keys defined in different code
# locations with automation conditions, only one of them actually launches runs
eligible_keys = {
    key
    for key in resolved_keys
    if (
        workspace_asset_graph.get_repository_handle(key).get_remote_origin()
        == repository_origin
    )
}
...
if sensor:
    # Each sensor owns the job keys recorded in its metadata (the default sensor
    # claims all job keys not explicitly distributed), so jobs are evaluated by
    # exactly one sensor.
    auto_materialize_entity_keys |= asset_job_keys_from_sensor_metadata(sensor.metadata)
else:
    # The sensorless daemon mode (`auto_materialize: use_sensors: false`): the
    # single global evaluation owns every conditioned job, added directly from
    # the graph being evaluated
    auto_materialize_entity_keys |= eligibility_graph.automatable_asset_job_keys
```

**Flow:** per (sensor, repo): resolve the sensor's selection against its repo's sub-graph → intersect with keys whose DEFINING repo origin equals this sensor's repo origin (duplicate definitions across locations collapse to one owner) → add claimed AssetJobKeys from metadata → evaluate conditions → runs tagged AUTO_MATERIALIZE/AUTOMATION_CONDITION/ASSET_EVALUATION_ID. Mid-submission enablement re-check every `check_after_runs_num` submissions via `_sensor_is_enabled` (pre-sensor mode also honors the global paused flag stored under `ASSET_DAEMON_PAUSED`, defaulting to PAUSED when unset — `get_auto_materialize_paused` returns `!= "false"`).
**Invariant:** Ownership is by definition-origin, not by name: two sensors can both select an asset key but only the one hosted where the key is DEFINED launches runs. Job-key claims are exclusive-by-metadata so jobs never double-evaluate across the default + custom sensors.
**Probe:** `python_modules/dagster/dagster_tests/declarative_automation_tests/daemon_tests/test_asset_daemon.py` and test_e2e.py (multi-sensor ownership scenarios).

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "ext-dagster", query: "asset_job_keys_from_sensor_metadata eligible_keys automation_condition", limit: 10 });
```

## Verdict
Adopt origin-scoped key ownership + explicit job-claim metadata; adapt to your asset-graph model; omit the pre-sensor single-global-tick mode if you always run sensor-based automation. Pinned by upstream declarative-automation daemon tests.
