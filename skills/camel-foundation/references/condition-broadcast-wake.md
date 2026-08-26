<!-- capsule-v2 -->
# Condition-broadcast wake ladder — Why does every channel mutation call notify_all, and why is the consumer a while-True?

**Source:** CAMEL-AI/camel Apache-2.0 `master@13dc7a7d`; Codebase Memory `ext-camel`. **Question:** How do blocked consumers get woken exactly when their predicate may now hold, without busy-waiting or lost wakeups?

## Predicate re-check loop with broadcast on EVERY state change
**Path/Symbol:** `camel/societies/workforce/task_channel.py:get_assigned_task_by_assignee` (:174-201), `get_returned_task_by_publisher` (:148-172).
**Signature:** `async def get_assigned_task_by_assignee(self, assignee_id: str) -> Task`.
**Data Shape:** Returns the claimed `Task`; suspends indefinitely until one matching packet exists; mutates channel state as a side effect (SENT→PROCESSING).

### Decisive source
```python
async with self._condition:
    while True:
        task_ids = self._task_by_assignee.get(assignee_id, deque())
        while task_ids:
            task_id = task_ids.popleft()
            if task_id in self._task_dict:
                packet = self._task_dict[task_id]
                if (packet.status == PacketStatus.SENT
                        and packet.assignee_id == assignee_id):
                    self._update_task_status(task_id, PacketStatus.PROCESSING)
                    self._condition.notify_all()
                    return packet.task
        await self._condition.wait()   # releases lock atomically
```

**Flow:** pop candidate ids → validate against `_task_dict` AND status AND assignee → claim or discard → if nothing valid, `wait()` (releases the condition lock) → any other method's `notify_all()` (post/return/archive/remove) re-wakes ALL waiters who re-run the predicate under the re-acquired lock.
**Invariant:** The wait must sit inside `while True`, not `if`: after wake another waiter may have consumed the task, so the predicate is ALWAYS re-checked. Every mutating path calls `notify_all()` even on no-op/removal because removals and status flips change what predicates hold. Stale deque entries are tolerated — validation against `_task_dict` filters them.
**Probe:** `grep -c 'await self._condition.wait()' camel/societies/workforce/task_channel.py` → 2 (one per blocking getter); `grep -c 'notify_all' camel/societies/workforce/task_channel.py` → 7.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-camel", query: "get_assigned_task_by_assignee atomic claim condition wait", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the notify-on-every-mutation + while-True-recheck pattern verbatim for condition-variable work queues; it is what makes lazy per-consumer queues safe. Adapt which predicate you check. Omit micro-opt `notify()` specialization — CAMEL deliberately broadcasts to keep correctness independent of waiter identity.
