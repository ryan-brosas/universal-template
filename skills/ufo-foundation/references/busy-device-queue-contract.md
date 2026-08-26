<!-- capsule-v2 -->
# Busy-device queue contract — Should a task submission to a busy worker block, queue, or fail?

**Source:** ufo (MIT) `main@96983c73ed09`; Codebase Memory `ufo`. **Question:** What is the admission contract when a task is assigned to a device that may already be executing something?

## Status-gated submit: queue behind BUSY, execute on IDLE
**Path/Symbol:** `galaxy/client/device_manager.py:ConstellationDeviceManager.assign_task_to_device` (:543-598); immediate-execution path `_execute_task_on_device` (:600-733); queued drain `_process_next_queued_task` (:735-748).
**Signature:** `async def assign_task_to_device(self, task_id: str, device_id: str, task_description: str, task_data: Dict[str, Any], timeout: float = 1000) -> ExecutionResult`.
**Data Shape:** Returns `ExecutionResult` (never raises for execution failures); raises ValueError only for admission violations; `timeout` defaults to 1000 (seconds per docstring) and rides inside the TaskRequest.

### Decisive source
```python
device_info = self.device_registry.get_device(device_id)
if not device_info:
    raise ValueError(f"Device {device_id} is not registered")
if device_info.status not in [DeviceStatus.CONNECTED, DeviceStatus.IDLE, DeviceStatus.BUSY]:
    raise ValueError(f"Device {device_id} is not connected (status: ...)")

if self.device_registry.is_device_busy(device_id):
    future = self.task_queue_manager.enqueue_task(device_id, task_request)
    result = await future          # caller still awaits ONE awaitable either way
    return result
else:
    return await self._execute_task_on_device(device_id, task_request)
```

**Flow:** admission gate (registered + status ∈ {CONNECTED, IDLE, BUSY}) → busy devices get the request enqueued per-device and the caller awaits the queue-issued future; idle devices execute inline → both branches are awaited identically by the caller, so the scheduler code never special-cases queuing.
**Invariant:** callers receive exactly one awaitable and one ExecutionResult regardless of queueing; disconnected/unregistered targets fail at admission with ValueError instead of silently queueing work that can never run.
**Probe:** direct source read :543-598 vs graph snippet (byte-parity); behavior cross-pinned from the consumer side by `tests/galaxy/client/test_pending_task_cancellation.py:137-205`, which drives assign_task_to_device through a mid-flight disconnect and asserts fast FAILED ExecutionResult. Coverage caveat: the pure BUSY-enqueue branch has no dedicated unit test at this pin.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ufo", name_pattern: ".*ConstellationDeviceManager\\.(assign_task_to_device|_execute_task_on_device|_process_next_queued_task)", limit: 10 });
```

## Verdict
Adopt the uniform-await contract: hide the queue-vs-inline decision behind one async submit so schedulers stay simple, and reject impossible submissions eagerly. Adapt the status vocabulary and default timeout to your transport (UFO's 1000 s default assumes slow GUI automation on remote devices). Omit per-device queueing if workers are single-tasked — but keep the admission ValueError ladder.
