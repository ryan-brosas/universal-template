<!-- capsule-v2 -->
# Asset daemon migration flags — how is the legacy single-cursor AMP world upgraded to per-sensor cursors exactly once?

**Source:** Dagster Apache-2.0 `master@4344eb7f4cf588c801c17489228790f002276aca`; Codebase Memory `ext-dagster`. **Question:** What one-time migrations run when the automation system moves to sensors, and what guarantees they don't re-run or half-run?

## Two daemon-lifetime migration keys, gated before first tick
**Path/Symbol:** `python_modules/dagster/dagster/_daemon/asset_daemon.py:_run_iteration_impl_with_request_context` migration block (lines 615-647) with helpers `_get_has_migrated`/`_set_has_migrated` (:134-157), `_create_initial_sensor_cursors_from_raw_cursor` (:738-805), `_copy_default_auto_materialize_sensor_states` (:807-842).
**Signature:** keys `_MIGRATED_CURSOR_TO_SENSORS_KEY = "MIGRATED_CURSOR_TO_SENSORS"`, `_MIGRATED_SENSOR_NAMES_KEY = "MIGRATED_SENSOR_NAMES_KEY"`; guard flag `self._checked_migrations` (in-memory, set after first successful check).
**Data Shape:** Migration 1: legacy pre-sensor cursor (from `ASSET_DAEMON_CURSOR_NEW`/legacy `ASSET_DAEMON_CURSOR`) is FILTERED per sensor — only condition cursors whose key ∈ that sensor's resolved selection survive (`dataclasses.replace(pre_sensor_cursor, previous_condition_cursors=condition_cursors)`). Migration 2: instigator states named `default_auto_materialize_sensor` copied to origins renamed `default_automation_condition_sensor`, preserving status + data.

### Decisive source
```python
if not self._checked_migrations:
    if not get_has_migrated_to_sensors(instance):
        # Do a one-time migration to create the cursors for each sensor, based on the
        # existing cursor for the legacy AMP tick
        ...
        if pre_sensor_cursor != AssetDaemonCursor.empty():
            self._logger.info(
                "Translating legacy cursor into a new cursor for each new automation policy sensor"
            )
            all_sensor_states = self._create_initial_sensor_cursors_from_raw_cursor(...)
        set_has_migrated_to_sensors(instance)
    if not get_has_migrated_sensor_names(instance):
        ...copy states...
        set_has_migrated_sensor_names(instance)

    self._checked_migrations = True
```

**Flow:** first iteration in sensor mode → check persistent flags in daemon_cursor_storage → migrate cursor-per-sensor (skipping sensors with empty selection; empty legacy cursor ⇒ just set the flag) → migrate default-sensor rename → mark both flags and the in-process guard so subsequent iterations skip entirely. New-state initial status honors the paused flag (`start_status = STOPPED if get_auto_materialize_paused(...) else RUNNING`).
**Invariant:** Migrations must be idempotent AND crash-tolerant: flags are written AFTER the migration work; a crash mid-migration replays it next start (cursor translation is derived data, safe to rebuild). The rename migration COPIES rather than moves so a version rollback still finds old rows.
**Probe:** `python_modules/dagster/dagster_tests/declarative_automation_tests/daemon_tests/test_asset_daemon.py` (migration scenarios).

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "ext-dagster", query: "_create_initial_sensor_cursors_from_raw_cursor _copy_default_auto_materialize_sensor_states", limit: 10 });
```

## Verdict
Adopt flagged-once derived-data migration with copy-not-move semantics for renames; adapt key names/storage; omit if greenfield. Pinned by upstream automation tests.
