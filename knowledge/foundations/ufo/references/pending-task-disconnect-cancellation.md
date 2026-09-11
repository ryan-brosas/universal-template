<!-- capsule-v2 -->
# Pending-task disconnect cancellation — What happens to in-flight work when a worker vanishes?

**Source:** ufo (MIT) `main@96983c73ed09`; Codebase Memory `ufo`. **Question:** How do callers waiting on a device's task future get unblocked immediately when that device disconnects, instead of hanging until timeout?

## Device-scoped future cancellation ladder
**Path/Symbol:** `galaxy/client/components/connection_manager.py:WebSocketConnectionManager._cancel_pending_tasks_for_device` (:509-543); orchestrating ladder `galaxy/client/device_manager.py:ConstellationDeviceManager._handle_device_disconnection` (:380-452).
**Signature:** `def _cancel_pending_tasks_for_device(self, device_id: str) -> None`; `async def _handle_device_disconnection(self, device_id: str) -> None`.
**Data Shape:** `_pending_tasks: Dict[task_id, (device_id, asyncio.Future)]` — the waiters registry keyed by task, valued by owning device; cancellation sets `ConnectionError("Device {id} disconnected while waiting for task response")` on each not-done future, then pops the entries.

### Decisive source
```python
tasks_to_cancel = [tid for tid, (dev, fut) in list(self._pending_tasks.items())
                   if dev == device_id and not fut.done()]
error = ConnectionError(f"Device {device_id} disconnected while waiting ...")
for task_id in tasks_to_cancel:
    _, task_future = self._pending_tasks.get(task_id)
    if not task_future.done():
        task_future.set_exception(error)
    self._pending_tasks.pop(task_id, None)

# device-manager ladder ordering in _handle_device_disconnection:
#   stop message handler → status=DISCONNECTED → connection teardown
#   → publish DEVICE_DISCONNECTED event → fail CURRENT task via
#     task_queue_manager.fail_task(device_id, current_task_id, ConnectionError)
#   → clear current_task_id → _schedule_reconnection(device_id)
```

**Flow:** disconnect event → the ordered ladder cleans state and notifies subscribers before recovery begins → every waiter whose future belongs to that device gets an immediate ConnectionError (only that device's futures — others stay pending) → reconnection is scheduled separately so cleanup never blocks retry.
**Invariant:** a vanished worker must never leave awaiters blocked past the disconnect; cancellation is scoped per-device (collateral futures untouched); done futures are skipped (never overwrite a real result); cleanup precedes reconnection scheduling.
**Probe:** `tests/galaxy/client/test_pending_task_cancellation.py:53-95` pins device-scoped cancel + entry removal; :99-134 pins disconnect-triggers-cancel; :137-205 (`test_task_returns_immediately_when_device_disconnects`) pins the end-to-end contract — assignee returns FAILED ExecutionResult with `metadata["disconnected"] is True` in <1 s against a 1000 s timeout.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ufo", name_pattern: ".*_cancel_pending_tasks_for_device.*", limit: 10 });
```

## Verdict
Adopt the waiter-registry shape: map task→(owner, future) so failure domains are derivable, cancel with set_exception scoped to the failed owner, skip done futures, and run full cleanup before any reconnect attempt. Adapt ConnectionError to your transport's failure type and keep `metadata["disconnected"]`-style flags so callers can distinguish disconnect-failures from task failures. Omit reconnection scheduling if your fleet replaces rather than revives workers.
