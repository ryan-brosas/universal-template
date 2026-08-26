<!-- capsule-v2 -->
# rtos-awareness-gdb-helpers — how do you show RTOS tasks as threads when the target has no OS-level debug API?

**Source:** JetBrains CLion installed build `2026.2.1@262.9437.136` (`bin/rtos/{common,freertos,zephyr,azure}`, 18 python modules); Codebase Memory `jetbrains-clion`. **Question:** How does a debugger surface FreeRTOS/Zephyr/Azure-RTOS threads, queues and heaps from raw memory without any runtime cooperation?

## One ABC, per-RTOS implementations
**Path/Symbol:** `bin/rtos/common/Rtos.py:class Rtos(ABC)` (11 `@abc.abstractmethod`); `freertos/__init__.py:FreeRtos.detect` (:45-53); `zephyr/__init__.py:Zephyr.detect` (:27-37); per-RTOS `cortex_m.py` context switching (`get_arm_cm_freertos_stacking` :60-116, `switch_zephyr_thread` :28-41).
**Signature:** static `detect() -> bool` + static `name()`; instance contract `get_threads / get_queues / get_timers / get_heap_info / get_config / get_current_thread / get_thread_registers / get_thread_stacking(stack_ptr)`.
**Data Shape:** task data is serialized as JSON strings back to the IDE (`json.dumps(task)`); TCB access via `gdb.lookup_symbol("pxCurrentTCB")` cast to a configured struct type; config flags degrade features (`use_trace_facility`, `is_smp`, `generate_runtime_stats`).

### Decisive source
```python
# freertos/Task.py:get_curr_task (direct read)
if config.is_smp:
    core_id = int(gdb.parse_and_eval("$_gthread")) - 1
    curr_tcb_ptr, _ = gdb.lookup_symbol("pxCurrentTCBs")
    ...
    if curr_tcb_val[core_id] == 0:
        return json.dumps("{}")
else:
    curr_tcb_ptr, _ = gdb.lookup_symbol("pxCurrentTCB")
    if curr_tcb_val == 0:
        return json.dumps("{}")

# feature degradation (get_freertos_tasks)
total_runtime, _ = gdb.lookup_symbol("ulTotalRunTime")
if total_runtime is None:
    config.generate_runtime_stats = False
```

**Flow:** detect() probes for RTOS-symbol fingerprints → IDE instantiates the matching implementation → enumerates kernel lists (`xPendingReadyList`, ...) through ListManager wrappers → renders threads/queues/heaps from TCB structs → cortex_m layer performs the context-register switch per thread.
**Invariant:** everything degrades silently when optional symbols are absent (zero TCB ⇒ `"{}"`, missing `ulTotalRunTime` ⇒ stats off); SMP vs single-core changes BOTH the symbol name (`pxCurrentTCBs` array indexed by `$_gthread-1`) AND the rendered state string; new RTOS support = one new module implementing the ABC, zero IDE-side changes. Helpers live ONLY under `bin/rtos` in this install (no plugin-dir twin).
**Probe:** executed byte-exact pre-write: `ls bin/rtos/*` → azure/common/freertos/zephyr trees; `grep -c "@abc.abstractmethod" common/Rtos.py` → `11`; twin check `ls plugins/nativeDebug-plugin/bin/rtos` → No such file.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-clion", query: "rtos detect threads freertos zephyr cortex", detail: "ids", limit: 12 });
```
(executed live this pass: Zephyr.detect :27-37, FreeRtos.detect :45-53, stacking helpers returned.)

## Verdict
Adopt symbol-fingerprint detection + per-OS strategy modules behind one interface with JSON serialization across the boundary; adapt TCB field names per kernel version; omit Cortex-M register dance unless you debug ARM targets. Coverage caveat: embedded-plane jars (clion-embedded/stm32) deferred — see work record NEXT-PASS TARGETS.