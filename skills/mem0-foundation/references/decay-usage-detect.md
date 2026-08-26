<!-- capsule-v2 -->
# Decay usage detection — how do repeated deletes betray "this user needs decayed memory" without inspecting message content?

**Source:** mem0 MIT `main@8d5b7865`; Codebase Memory `mnt-hdd-utopia-inspo-memory-mem0`. **Question:** what signal converts delete traffic into a decay-feature trigger, and where do its counters live (process vs persisted) relative to every other notice's?

## Connected graph-selected seam
**Path/Symbol:** `mem0/memory/notices.py`: `DECAY_USAGE_DELETE_THRESHOLD=5` (:32), `detect_decay_usage_from_delete` (:256-273), `detect_decay_usage_from_delete_all` (:276-284), consumed by `display_decay_usage_notice` (:287-374, delete_count/deleted_count event fields :365-366). Direct tests `tests/memory/test_decay_usage_notice.py` (250L dedicated suite).
**Signature:** `detect_decay_usage_from_delete() -> Optional[Tuple[str,str,Optional[int],Optional[int]]]`; `detect_decay_usage_from_delete_all(deleted_count: Any) -> Optional[Tuple[...]]`.
**Data Shape:** return tuples `(source, reason, delete_count, deleted_count)` — single-delete path fills `("delete_count","repeated_deletes",N,None)` once N≥5; delete-all path returns `("delete_all","bulk_delete",None,count)` for EVERY positive call (coerced via `_coerce_nonnegative_int`, ≤0 → None).

### Decisive source
```python
def detect_decay_usage_from_delete():
    global _decay_usage_successful_delete_count_in_process
    with _state_lock:
        if _decay_usage_capacity_reached_in_process:
            return None
        _decay_usage_successful_delete_count_in_process += 1
        delete_count = _decay_usage_successful_delete_count_in_process
    # threshold check OUTSIDE the lock, capacity re-check inside display
    if delete_count >= DECAY_USAGE_DELETE_THRESHOLD and not _decay_usage_at_capacity():
        return ("delete_count", "repeated_deletes", delete_count, None)

def detect_decay_usage_from_delete_all(deleted_count):
    deleted_count_value = _coerce_nonnegative_int(deleted_count, 0)
    if deleted_count_value <= 0: return None
    return ("delete_all", "bulk_delete", None, deleted_count_value)
```

**Flow:** every successful single delete increments an in-process counter under `_state_lock`; at ≥5 AND while the 7-day/cap-10 ledger has room, the detector hands a trigger to `display_decay_usage_notice`, which runs the standard flag→payload→record→capture→stderr pipeline. delete_all short-circuits: any positive deleted count is immediately a bulk_delete trigger (no threshold). Unlike first-run/scale flags NOTHING here persists a consumed marker — only the cap/window ledger in config bounds repetition.
**Invariant:** (1) the delete counter is PROCESS-local and never persisted — restart resets the 5-strike ladder by design (delete volume within one process lifetime is the signal); (2) increment happens under lock but the threshold branch evaluates after release — two racing deletes can both pass at 5/6, which is acceptable because the display-side ledger caps total notices anyway; (3) `deleted_count<=0` (including bool True coerced? no — `_coerce_nonnegative_int` rejects bools explicitly) yields None so failed/no-op delete_alls never trigger; (4) capacity latch is shared with all other usage notices' pattern: once saturated, detection keeps returning None forever in-process.
**Probe:** `tests/memory/test_decay_usage_notice.py` (threshold crossing on 5th delete, reset-on-fixture proof, bulk path coercion matrix).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-memory-mem0", query: "detect_decay_usage_from_delete detect_decay_usage_from_delete_all", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the strike-counter + bulk-shortcut duality verbatim (they answer different user stories: slow staleness vs hard reset); adapt the threshold (5) to your product telemetry budget; omit the process-local nuance ONLY if your deletes are rare enough that persistence costs more than it buys.
