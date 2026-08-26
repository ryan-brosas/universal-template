<!-- capsule-v2 -->
# OSS notice state machine — how do best-effort product notices stay once-ever, rate-capped, and unable to break or spam a memory operation?

**Source:** mem0 MIT `main@8d5b7865`; Codebase Memory `mnt-hdd-utopia-inspo-memory-mem0`. **Question:** how does one module drive five distinct product notices (first-run, temporal/decay/scale/slow-query usage) so that telemetry outage can never fail a user call, no notice repeats beyond its cap, and the claim survives process restarts?

## Connected graph-selected seam
**Path/Symbol:** `mem0/memory/notices.py`: constants (:13-49), module-global latch state under `_state_lock` (:67-77), `display_first_run_notice` (:80-146) + `_claim_first_run_notice` (:853-880) + `_update_first_run_variant` (:883-898); capacity trio `_temporal_usage_at_capacity` (:985-999) / `_record_temporal_usage_opportunity` (:1002-1045) / `_recent_temporal_usage_entries` (:1048-1069); feature-error twin `_feature_error_at_capacity` (:901-914) + `_get_feature_error_message` (:737-818); provider-count probe `_get_provider_memory_count` (:1404-1448) + `_extract_count` (:1451-1476). Direct tests `tests/memory/test_notices.py` (1,551L; autouse fixture resets every module global :26-45) + dedicated suites `tests/memory/test_temporal_usage_notice.py` (202L), `tests/memory/test_decay_usage_notice.py` (250L), `tests/memory/test_performance_slow_query_notice.py` (445L).
**Signature:** `display_first_run_notice(memory_instance, sync_type: str, trigger_function: str) -> None`; `_claim_first_run_notice(trigger_function: str) -> bool`; `_record_*_opportunity(**fields) -> bool`; `_recent_*_entries(config, now) -> list`.
**Data Shape:** durable state lives inside `~/.mem0/config.json` under section `notice_state.<state_key>` as `{events: [{evaluated_at: iso, variant, sync_type, ...}], ...flags}`; every counter pair is `(CAP=10, WINDOW=timedelta(days=7))` except first-run (once ever, no cap) and decay-delete detection (threshold `DECAY_USAGE_DELETE_THRESHOLD=5`). Module globals are process-level fast-path latches only.

### Decisive source
```python
# once-EVER claim: persisted BEFORE any flag check, so an offline first call burns the slot
def _claim_first_run_notice(trigger_function: str) -> bool:
    global _first_run_claimed_in_process
    with _state_lock:
        if _first_run_claimed_in_process:
            return False
        config = _load_config()
        state = config.get(STATE_SECTION)
        if isinstance(state, dict):
            first_run = state.get(STATE_KEY)
            if isinstance(first_run, dict) and first_run.get("consumed"):
                _first_run_claimed_in_process = True
                return False
        ...
        state[STATE_KEY] = {"consumed": True,
                            "consumed_at": datetime.now(timezone.utc).isoformat(),
                            "trigger_function": trigger_function, "variant": None}
        config[STATE_SECTION] = state
        _write_config(config)                      # atomic tempfile+fsync (setup.py)
        _first_run_claimed_in_process = True
        return True

# READ is FAIL-CLOSED (treat errors as saturated), WRITE is FAIL-SILENT (drop the notice)
def _temporal_usage_at_capacity() -> bool:
    if _temporal_usage_capacity_reached_in_process: return True   # latch: never re-read after cap
    try:
        with _state_lock:
            entries = _recent_temporal_usage_entries(_load_config(), datetime.now(timezone.utc))
            at_capacity = len(entries) >= TEMPORAL_USAGE_CAP       # 10
            if at_capacity: _temporal_usage_capacity_reached_in_process = True
            return at_capacity
    except Exception:
        return True                                                # ← read fails ⇒ act as capped
```
```python
# sliding window filter: unparseable timestamps DROP OUT silently (never count, never crash)
cutoff = now - TEMPORAL_USAGE_WINDOW
for entry in entries:
    evaluated_at = _parse_datetime(entry.get("evaluated_at"))
    if evaluated_at is not None and evaluated_at >= cutoff:
        recent.append(entry)
```

**Flow:** caller (Memory.add/search/delete wrappers) → telemetry-enabled gate → process-latch short-circuit → flag evaluation (PostHog variant `displayed|holdout`) → payload notice-config arbitration (`missing_notice_config` → `payload_disabled` → `missing_copy` → `holdout`/`not_displayed` bypass reasons recorded on EVERY evaluation) → `_record_*_opportunity` re-checks capacity under lock, appends entry, persists whole config → `capture_event(NOTICE_EVENT)` → `print(copy, file=sys.stderr)` ONLY when `variant=="displayed"` AND enabled AND copy non-empty. First-run additionally claims-before-flag-eval and backfills `"variant"` even when the flag call raised (:144-146).
**Invariant:** (1) every public entry point swallows all exceptions — a notice can never fail a memory op ("Never raises or writes unless displayed"); (2) first-run consumes exactly once GLOBALLY (persisted claim precedes flag lookup — offline still burns it); (3) usage notices show ≤10 times per rolling 7-day window, and the process latch means the config file is never re-read after saturation; (4) read-side capacity checks fail CLOSED (error ⇒ treat as at-capacity) while write-side record fails OPEN-silent (error ⇒ drop notice, continue); (5) holdout variants get telemetry events but NEVER stderr output — except feature-error messages where BOTH displayed and holdout return remote copy over the plain fallback (:780-783 asymmetry); (6) `_render_scale_copy` falls back to the raw template on format errors instead of dropping the notice (:1479-1485).
**Probe:** `tests/memory/test_notices.py::detect_temporal_usage_from_search returns ("filter","date_range_filter") for gt/gte/lt/lte on date-like keys` (:614-663 matrix incl. `{score:{gte:0.5}}`→None negative); dedicated `tests/memory/test_temporal_usage_notice.py` pins cap/window arithmetic against a fake `_load/_write_config` harness; autouse `reset_notice_process_state` proves the module-global latch set is the full observable state.
**Coverage caveat:** scale-threshold notice has NO standalone suite file — covered only inside test_notices.py; TS twin `mem0-ts/src/oss/src/utils/notices.ts` exists but is out of this Python graph's cited scope here.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-memory-mem0", query: "_claim_first_run_notice _record_temporal_usage_opportunity _temporal_usage_at_capacity", limit: 10, fields: ["signature", "name", "file"] });
```
(resolved: `mnt-hdd-utopia-inspo-memory-mem0.mem0.memory.notices._is_temporal_key` Function mem0/memory/notices.py 1521-1542 among ≥4 hits)

## Verdict
Adopt the claim-before-flag first-run protocol, the CAP/WINDOW sliding-window ledger shape, and the fail-closed-read/fail-open-write asymmetry verbatim; adapt notice IDs/copy keys to your product's flag payload; omit PostHog specifics if your flags come from elsewhere (keep the bypass-reason taxonomy — it is what makes the events debuggable).
