<!-- capsule-v2 -->
# pydevd settrace attach handshake — what ordering makes attach-safe suspend work?

**Source:** JetBrains PyCharm installed distribution (proprietary packaging; helper sources carry Apache-2.0 headers — study/reference use only) pin `?@?` build PY-262.9437.214 (non-git; freshness = product-info.json buildNumber re-read unchanged); Codebase Memory project `jetbrains-pycharm` (full mode, 103533 nodes). **Question:** In what order must connect, tracing, and first-suspend happen so attaching never loses a breakpoint?

## Lock-guarded connect → busy-wait handshake → trace → suspend LAST
**Path/Symbol:** `plugins/python-ce/helpers/pydev/pydevd.py`:1810-1857 `settrace`; :1862-1976 `_locked_settrace`; :1860 `_set_trace_lock`.
**Signature:** `settrace(host=None, stdout_to_server=False, stderr_to_server=False, port=5678, suspend=True, trace_only_current_thread=False, overwrite_prev_trace=False, patch_multiprocessing=False, stop_at_frame=None)`.
**Data Shape:** returns nothing; global `connected` flips only after `py_db.connect` succeeds; handshake completes when `py_db.ready_to_run` becomes truthy.

### Decisive source
```python
while not py_db.ready_to_run:
    time.sleep(0.1)  # busy wait until we receive run command
py_db.set_trace_for_frame_and_parents(get_frame().f_back)
...
py_db.enable_tracing(apply_to_all_threads=True)
...
atexit.register(stoptrace)
# Suspend as the last thing after all tracing is in place.
if suspend:
    if stop_at_frame is not None:
        additional_info.pydev_state = STATE_RUN
        additional_info.pydev_step_cmd = CMD_STEP_OVER
        additional_info.pydev_step_stop = stop_at_frame
    else:
        py_db.set_suspend(t, CMD_SET_BREAK)
```
(`ready_to_run` is flipped by `process_net_command` on `CMD_RUN`, pydevd_process_net_command.py:104-105.)

**Flow:** acquire lock → optional `patch_new_process_functions` → resolve localhost → `PyDB()` + `connect(host, port)` → `connected = True` → stdout/stderr redirect + stdin patch → busy-wait for `CMD_RUN` → trace caller frame (`f_back`) + custom frames → start aux daemon threads → `enable_tracing(apply_to_all_threads=True)` → future-thread patch unless `trace_only_current_thread` or `USE_LOW_IMPACT_MONITORING` → register `atexit stoptrace` → THEN suspend (emulated step via `STATE_RUN + CMD_STEP_OVER + step_stop` frame when `stop_at_frame`, else `set_suspend(t, CMD_SET_BREAK)`). A second `settrace` on a live session skips reconnect and just re-traces (`else` branch :1951-1963).
**Invariant:** Never suspend before tracing is fully in place; `connected` may flip only after a successful socket connect; suspend-at-entry is expressed as a pending STEP command, never a synthetic break event.
**Probe:** executed 2026-08-25 — `PASS port default 5678 / suspend default True / stop_at_frame param present`; order check `PASS suspend ordered AFTER tracing in place` (index of `enable_tracing(apply_to_all_threads=True)` < index of `py_db.set_suspend(t, CMD_SET_BREAK)` inside `_locked_settrace` source); `PASS busy-wait ready_to_run handshake`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.get_code_snippet({ project: "jetbrains-pycharm", qualified_name: "jetbrains-pycharm.plugins.python-ce.helpers.pydev.pydevd._locked_settrace" });
// -> start_line 1862 end_line 1976 — EXECUTED (matches direct read byte-for-byte)
```

## Verdict
Adopt the ordering discipline (connect → handshake → trace everything → suspend last) and the emulated-step encoding of stop-at-frame. Adapt transport details (socket pair, busy-wait poll interval). Omit Jython/Python-2 fallbacks (`thread.allocate_lock`, `sys.exc_clear`).