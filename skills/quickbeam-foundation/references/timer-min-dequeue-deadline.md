<!-- capsule-v2 -->
# timer-min-dequeue-deadline — How does one thread multiplex timers, message waits, and eval deadlines?

**Source:** QuickBEAM MIT `master@c21c0e31`; Codebase Memory `ext-quickbeam`. **Question:** How does the pool thread block on incoming work without starving setTimeout across all hosted contexts?

## min-timer bounded dequeue seam
**Path/Symbol:** `lib/quickbeam/context_worker.zig:pool_worker_main` loop (:144-172), `find_min_timer/1` (:179-188), `fire_all_timers/1` (:190-196); deadline consumer `interrupt_handler/2` (:14-20).
**Signature:** `ct.pool_dequeue_blocking(pd, min_timer_ns orelse null)`; `pd.deadline: ?i128`; `JS_SetInterruptHandler(rt, &interrupt_handler, pd)`.
**Data Shape:** Per-context timer maps consulted for the global minimum; a null timeout means block indefinitely; deadline is SHARED pool state written per-eval.

### Decisive source
```zig
while (true) {
    const min_timer_ns = find_min_timer(&contexts);
    const msg = if (min_timer_ns != null and min_timer_ns.? == 0)
        ct.pool_dequeue(pd)                       // timer due NOW: drain non-blocking
    else
        ct.pool_dequeue_blocking(pd, min_timer_ns orelse null);
    if (msg) |m| { switch (m) { ... } }
    fire_all_timers(&contexts);                   // every context, then drain jobs
}

fn interrupt_handler(_: ?*qjs.JSRuntime, user_data: ?*anyopaque) c_int {
    const pd: *ct.PoolData = @ptrCast(@alignCast(user_data));
    if (pd.deadline) |deadline| { if (sync.nowNanoseconds() > deadline) return 1; }
    return 0;
}
```

**Flow:** compute earliest timer across ALL contexts → due-now ⇒ poll queue without blocking; else bounded-block until that instant → handle any message → fire expired timers + drain microtasks in every context → repeat. Eval timeouts ride the same structure: handle_ctx_eval sets `pd.deadline`, the interrupt handler checks it inside the engine and aborts execution when exceeded; deadline cleared after.
**Invariant:** (1) The blocking wait must wake at-or-before the earliest timer or setTimeout latency becomes unbounded — the `== 0 ⇒ non-blocking` special case prevents a busy spin between "due" and "fired". (2) One shared deadline field means concurrent evals on different contexts of the SAME thread would stomp each other — safe only because thread serializes evals; porters adding parallelism break this silently. (3) fire_all_timers runs even after control messages, so timers can't be starved by a chatty queue.
**Probe:** `grep -c 'find_min_timer' lib/quickbeam/context_worker.zig` → 2.
**Probe:** `grep -c 'pd.deadline' lib/quickbeam/context_worker.zig` → 5.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-quickbeam", query: "interrupt handler deadline find_min_timer blocking dequeue", limit: 10 });
```

## Verdict
Adopt min-timer-bounded blocking as the event-loop sleep primitive for multi-context hosts; adapt the deadline mechanism to your engine's interrupt API; keep the shared-deadline-is-serial caveat documented wherever you port it. Coverage: context_worker.zig no_recorded_issue; behavior pinned by test/core/timeout_test.exs at the pin.
