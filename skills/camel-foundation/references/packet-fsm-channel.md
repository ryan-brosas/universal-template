<!-- capsule-v2 -->
# Packet FSM task channel — How does a multi-agent workforce exchange tasks without races or lost wakeups?

**Source:** CAMEL-AI/camel Apache-2.0 `master@13dc7a7dda66d943949e5448d55e70d5a9481cfe`; Codebase Memory `ext-camel`. **Question:** What data structure and state machine let N workers claim tasks concurrently with no double-claim, no missed post, and clean removal?

## Hybrid-index channel guarded by ONE asyncio.Condition
**Path/Symbol:** `camel/societies/workforce/task_channel.py:TaskChannel` (`__init__` :94-103, `_update_task_status` :105-120).
**Signature:** `TaskChannel()`; internal `_condition: asyncio.Condition`, `_task_dict: Dict[str, Packet]`, `_task_by_status: Dict[PacketStatus, Set[str]]` (defaultdict(set)), `_task_by_assignee/_task_by_publisher: Dict[str, deque[str]]` (defaultdict(deque)).
**Data Shape:** `Packet(task, publisher_id, assignee_id=None, status=SENT)`; statuses `SENT → PROCESSING → RETURNED → ARCHIVED`. Assignee/publisher deques hold *ids in arrival order*; status sets hold *membership*. Every public method takes `async with self._condition` — there is exactly one lock for the whole channel.

### Decisive source
```python
def _update_task_status(self, task_id, new_status):
    if task_id not in self._task_dict:
        return
    packet = self._task_dict[task_id]
    old_status = packet.status
    if old_status in self._task_by_status:
        self._task_by_status[old_status].discard(task_id)
    packet.status = new_status
    self._task_by_status[new_status].add(task_id)
```

**Flow:** `post_task` inserts into all three indexes as SENT + notify_all → worker's `get_assigned_task_by_assignee` pops its deque, validates SENT+assignee match, flips to PROCESSING via the helper, returns task under the lock (atomic claim) → worker later `return_task` flips to RETURNED only `if status != RETURNED` (idempotent) and appends to the *publisher's* deque → publisher's `get_returned_task_by_publisher` pops, cleans ALL indexes, deletes from dict, notifies waiters.
**Invariant:** A task id lives in exactly one status set and at most one assignee deque at a time; every mutation happens under the single condition lock, so claim/return/remove are linearizable. Status transitions MUST go through `_update_task_status` or the status index silently desyncs from `_task_dict`.
**Probe:** `grep -c 'async with self._condition' camel/societies/workforce/task_channel.py` → 11 (every public method); `grep -c '_update_task_status' camel/societies/workforce/task_channel.py` → 4 (definition + 3 transition sites: claim :195, return :236, archive :257).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-camel", query: "TaskChannel post_task return_task Packet", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the hybrid index (dict for O(1) id lookup + status sets + ordered per-party deques) and the single-condition-lock discipline for any ported work queue. Adapt PacketStatus names to host vocabulary. Omit the defensive duplicate-status warning path (`get_in_flight_tasks` :301-309) unless you keep all four statuses.
