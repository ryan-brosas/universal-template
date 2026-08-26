<!-- capsule-v2 -->
# Threshold + one-shot jitter — how does a scheduler randomize check timing without drifting or hot-looping?

**Source:** changedetection.io Apache-2.0 `master@fce24780`; Codebase Memory `ext-changedetection.io`. **Question:** How are per-watch vs global thresholds combined, and why is jitter drawn once and then reset?

## Connected graph-selected seam
**Path/Symbol:** `changedetectionio/flask_app.py:ticker_thread_check_time_launch_checks` (:1308-1322, :1363); `model/Watch.py:threshold_seconds` (:747-753), `jitter_seconds = 0` attr (:232); `store/__init__.py:threshold_seconds` property (:571-578); `mtable` units map in Watch model.
**Signature:** Watch: `threshold_seconds(self) -> int` sums `time_between_check[unit] * mtable[unit]`; store-level property mirrors it against global settings. Jitter: `watch.jitter_seconds = random.uniform(-abs(jitter), jitter)`.
**Data Shape:** `mtable` maps user units (seconds/minutes/hours/days/weeks) → seconds. `recheck_time_minimum_seconds = int(os.getenv('MINIMUM_SECONDS_RECHECK_TIME', 3))`.

### Decisive source
```python
# #580 - Jitter plus/minus amount of time to make the check seem more random to the server
jitter = datastore.data['settings']['requests'].get('jitter_seconds', 0)
if jitter > 0:
    if watch.jitter_seconds == 0:
        watch.jitter_seconds = random.uniform(-abs(jitter), jitter)
...
if seconds_since_last_recheck >= (threshold + watch.jitter_seconds) and seconds_since_last_recheck >= recheck_time_minimum_seconds:
...
    # Reset for next time
    watch.jitter_seconds = 0
```
```python
def threshold_seconds(self):
    seconds = 0
    for m, n in mtable.items():
        x = self.get('time_between_check', {}).get(m, None)
        if x:
            seconds += x * n
    return seconds
```

**Flow:** Effective due-time = threshold (watch-level if any unit set, else global) + jitter offset. The jitter value is drawn ONCE per scheduling cycle, kept on the watch (`== 0` means "no draw yet"), used as a stable offset so the due comparison doesn't re-randomize every second the ticker loops, and zeroed after successful enqueue so next cycle gets a fresh draw. Negative draws make checks slightly EARLY relative to threshold; the system-wide 3s floor prevents negative/zero-threshold hot-looping.
**Invariant:** Threshold selection is exclusive: `time_between_check_use_default` picks global store threshold; otherwise watch's own sum — never both. A porter who redraws jitter each loop iteration makes due-time flicker across the threshold and can enqueue repeatedly.
**Probe:** `grep -c 'random.uniform' changedetectionio/flask_app.py` → `1`; `grep -c 'MINIMUM_SECONDS_RECHECK_TIME' changedetectionio/flask_app.py` → `2`; `grep -c 'def threshold_seconds' changedetectionio/model/Watch.py` → `1`.
**Direct test:** `tests/test_scheduler.py:test_check_basic_global_scheduler_functionality` pins global-schedule gating; per-watch threshold sums exercised via watch-model unit tests (`tests/unit/test_watch_model.py`) and edit-form flows.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-changedetection.io", query: "jitter_seconds threshold time_between_check", limit: 5 });
// → Watch.threshold_seconds Method model/Watch.py + ticker caller flask_app.py
```

## Verdict
Adopt draw-once-reset-after-use jitter plus additive threshold selection for polite polling schedulers. Adapt the units map. Omit jitter entirely if your targets aren't rate-limit-sensitive (but keep the floor).
