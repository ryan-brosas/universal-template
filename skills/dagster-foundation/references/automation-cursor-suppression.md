<!-- capsule-v2 -->
# AutomationConditionSensor cursor suppression — why are automation ticks stored WITHOUT their cursor?

**Source:** Dagster Apache-2.0 `master@4344eb7f4cf588c801c17489228790f002276aca`; Codebase Memory `ext-dagster`. **Question:** What is written to the tick row for AUTOMATION-type sensors and why does it differ from regular sensors?

## Tick rows carry no cursor for automation sensors
**Path/Symbol:** `python_modules/dagster/dagster/_daemon/sensor.py:SensorLaunchContext._write` (lines 232-238).
**Signature:** `def _write(self) -> None` — the single funnel through which every sensor tick update is persisted.
**Data Shape:** Branch condition: `self._remote_sensor.sensor_type == SensorType.AUTOMATION`; otherwise full tick (including cursor) persisted.

### Decisive source
```python
def _write(self) -> None:
    # do not write the cursor into the ticks table for custom user-code AutomationConditionSensorDefinitions
    if self._remote_sensor.sensor_type == SensorType.AUTOMATION:
        self._instance.update_tick(self._tick.with_cursor(None))
    else:
        self._instance.update_tick(self._tick)
```

**Flow:** For DA sensors, the authoritative cursor lives in the instigator STATE (`SensorInstigatorData.cursor`, written by the asset daemon after evaluation — see asset-tick-evaluation-gate), not in each tick row; tick rows get `cursor=None`. Regular sensors persist their cursor per finished tick because `_write`'s second half uses `self._tick.cursor` to update state on success. The UI reads evaluations via `evaluation_id` (= tick id) rather than cursors.
**Invariant:** One source of truth for the DA cursor prevents divergence between what a resumed tick believes and what the next fresh tick evaluates against; porting a "write cursor everywhere" design would resurrect the crash-window inconsistency the split exists to avoid.
**Probe:** `python_modules/dagster/dagster_tests/declarative_automation_tests/daemon_tests/test_asset_daemon.py` (tick-row cursor assertions in DA scenarios).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-dagster", query: "SensorType.AUTOMATION with_cursor update_tick", limit: 10 });
```

## Verdict
Adopt single-source-of-truth cursor placement per instigator family; adapt storage split to your schema; omit if you have no dual sensor/automation families.
