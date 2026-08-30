<!-- capsule-v2 -->
# Asset daemon cursor versioning — how is a 30-day automation state serialized safely across upgrades?

**Source:** Dagster Apache-2.0 `master@4344eb7f4cf588c801c17489228790f002276aca`; Codebase Memory `ext-dagster`. **Question:** What is the on-disk format of the auto-materialization cursor and which corruptions must a reader survive?

## Version-prefixed b64(zlib(serdes)) with foreign-cursor quarantine
**Path/Symbol:** `python_modules/dagster/dagster/_daemon/asset_daemon.py:asset_daemon_cursor_to_instigator_serialized_cursor` (lines 234-257) + `asset_daemon_cursor_from_instigator_serialized_cursor` (:294-325) + `_is_foreign_sensor_cursor` (:284-291) + `_CURSOR_COLUMNAR_CLASSES` (:100-111).
**Signature:** `def asset_daemon_cursor_to_instigator_serialized_cursor(cursor: AssetDaemonCursor) -> str` (returns `VERSION + base64(zlib(bytes))`, VERSION ∈ {"0","1"}).
**Data Shape:** v1 (env `DAGSTER_WRITE_COMPRESSED_ASSET_DAEMON_CURSOR`) uses columnar dedup packing for high-repetition classes: `{"AutomationConditionNodeCursor","AssetSubset","AssetKey","AutomationConditionCursor","TimeWindow","TimestampWithTimezone","TimeWindowPartitionsSubset","TimeWindowPartitionsDefinition"}` — "deploy the reader change first before enabling the writer via the env var".

### Decisive source
```python
def _is_foreign_sensor_cursor(serialized_cursor: str) -> bool:
    """...Valid DA cursors are always a version-digit prefix followed by base64
    and never start with ``{``, so this check does not overlap with any legitimate format."""
    return serialized_cursor.startswith('{"__class__":')
...
if _is_foreign_sensor_cursor(serialized_cursor):
    # Treat as empty so the next successful tick overwrites it with a valid DA cursor.
    # We do NOT generalize this to "any unknown version" on purpose to ensure that other
    # unexpected states do not wipe out valid cursor state.
    ...
    return AssetDaemonCursor.empty()

version, encoded_bytes = serialized_cursor[0], serialized_cursor[1:]
if version not in ("0", "1"):
    raise DagsterInvariantViolationError(f"Invalid serialized cursor version: {version}")
```

**Flow:** write path also skips expensive partition-count pre-computation (`skip_num_partitions_serialization_ctx()`) — pure perf. Read path ladder: None ⇒ empty; `{"__class__":` prefix ⇒ known past-migration-bug corruption ⇒ empty + warning (quarantine); version digit 0 ⇒ legacy wrapper conversion (`LegacyAssetDaemonCursorWrapper.get_asset_daemon_cursor(asset_graph)`); 1 ⇒ columnar deserialization; anything else ⇒ hard error (never silently wipe). Migration keys `MIGRATED_CURSOR_TO_SENSORS` / legacy `ASSET_DAEMON_CURSOR`→`ASSET_DAEMON_CURSOR_NEW` handled once per daemon lifetime via daemon_cursor_storage flags (`get_has_migrated_to_sensors` :144-157).
**Invariant:** Unknown-but-well-formed state raises; only the EXACT known corruption signature is discarded — generalizing the discard rule would let future bugs erase valid evaluation history (evaluation_id monotonicity is what makes tick retry decisions safe). Reader-first rollout ordering is mandatory for new versions.
**Probe:** `python_modules/dagster/dagster_tests/declarative_automation_tests/daemon_tests/test_asset_daemon.py` (cursor round-trips + migration scenarios).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-dagster", query: "asset_daemon_cursor serialize deserialize LegacyAssetDaemonCursorWrapper", limit: 10 });
```

## Verdict
Adopt version-prefix envelope + explicit corruption quarantine + unknown-version raise; adapt serdes/columnar packing to your formats; omit the specific migration-key history if greenfield. Pinned by upstream automation daemon tests.
