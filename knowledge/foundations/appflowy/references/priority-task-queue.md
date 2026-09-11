<!-- capsule-v2 -->
# Priority task queue — how do you schedule background jobs with QoS classes when your "queue" is secretly a max-heap that runs newest-first?

**Source:** AppFlowy AGPL-3.0 `main@5cf3a365dec0d59f64bad1ee4bb1050471a39b93`; Codebase Memory `ext-appflowy`. **Question:** In what order do queued tasks actually execute across QoS levels and within one handler, and which lifecycle states can a task pass through?

## TaskQueue/TaskDispatcher: QoS-desc, then id-desc
**Path/Symbol:** `frontend/rust-lib/lib-infra/src/priority_task/task.rs:PendingTask::Ord` (:38-58) + `queue.rs:TaskQueue` (:8-74, debug-assert :36-39) + `scheduler.rs:TaskDispatcher.process_next_task` (:61-100).
**Signature:** `impl Ord for PendingTask { fn cmp(&self, other) { match (self.qos, other.qos) { (UI, UI) => self.id.cmp(&other.id), (UI, _) => Greater, (_, UI) => Less, (BG, BG) => self.id.cmp(&other.id) } } }`.
**Data Shape:** `QualityOfService::{Background, UserInteractive}`; `TaskId=u32` from an AtomicU32 counter; states `Pending→Processing→{Done|Failure|Timeout|Cancel}`; result via per-task tokio oneshot.

### Decisive source
```rust
// queue.rs :30-43 — ids must be NON-DECREASING per handler (debug_assert), heap is a MAX-heap
match self.index_tasks.entry(task.handler_id.clone()) {
  Entry::Occupied(entry) => { let mut list = entry.get().borrow_mut();
    debug_assert!(list.peek().map(|old_id| pending_task.id >= old_id.id).unwrap_or(true));
    list.push(pending_task); },
  ...
}
// scheduler.rs :66-72 — cancel is checked AFTER dequeue, before running
if task.state().is_cancel() { let _ = ret.send(task.into()); self.notify(); return None; }
```
```rust
// scheduler.rs :78-96 — per-task timeout wraps the handler; missing handler = Cancel state
task.set_state(TaskState::Processing);
match tokio::time::timeout(self.timeout, handler.run(content)).await {
  Ok(Ok(_)) => task.set_state(TaskState::Done),
  Ok(Err(e)) => { /* log */ task.set_state(TaskState::Failure) },
  Err(e)    => { /* log */ task.set_state(TaskState::Timeout) },
}
```

**Flow:** `add_task` pushes into a per-handler BinaryHeap (grouped in an outer heap keyed by each list's head) + TaskStore, then notifies. The runner wakes on the watch channel, waits ONE interval tick of 300ms (created fresh INSIDE the loop — so it's a fixed-rate poll, not a coalescing debounce), pops the winning head-list, pops its max task. Cancelled tasks are removed from the store at pop time and answer their oneshot with Cancel; empty-content tasks are dropped at PUSH time (`queue.push` warns and returns) leaving the store entry stranded forever.
**Invariant:** Execution order = UserInteractive first, then Background; WITHIN a level, HIGHEST id first (LIFO for monotonic ids — verified live: [100,200,300] ran as [300,200,100]). A porter assuming FIFO will reorder background work. Timeout does NOT abort the handler future's work product — it just marks state while the future keeps running to completion inside the timeout wrapper's dropped context.
**Probe:** `/tmp/extcollab-af-probe` t06 (LIFO order [300,200,100]), t07 (UI preempts BG added earlier), t08 (cancel → oneshot Cancel + store removal), t09 (slow → Timeout delivered), t10 (empty content never runs, store entry retained), t06b (documents internal-only monotonic-id guard) — all executed GREEN at this pin.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-appflowy", query: "TaskQueue mut_head push BinaryHeap PendingTask Ord", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-level QoS heap and the pop-time cancel protocol. Adapt tick cadence and QoS vocabulary. Omit the outer grouped heap if you have few handlers — a single heap preserves the ordering contract.
