<!-- capsule-v2 -->
# drain-callback-promise-pump — How can a busy JS context receive async replies while it is mid-await?

**Source:** QuickBEAM MIT `master@c21c0e31`; Codebase Memory `ext-quickbeam`. **Question:** When one context blocks the pool thread awaiting a promise, how do resolution messages for OTHER contexts (and its own) get delivered?

## Thread-local drain callback seam
**Path/Symbol:** `lib/quickbeam/context_worker.zig:install_pump/4` (:28-44), `pool_drain_callback/1` (:46-104), install/uninstall bracketing in `handle_ctx_eval` (:303-317) and `handle_ctx_call` (:352-366).
**Signature:** `entry.state.drain_fn = &pool_drain_callback;` plus threadlocals `tl_pool_data`, `tl_contexts`, `tl_context_id`; QuickJS invokes the registered drain_fn whenever the engine yields (microtask checkpoint / await suspension).
**Data Shape:** Pool queue messages tagged per context; resolve/reject/message/define/get arms process immediately if `p.context_id == active_id`, else route via handle_ctx_* to the target entry's queue.

### Decisive source
```zig
fn pool_drain_callback(state: *worker.WorkerState) void {
    const pd = tl_pool_data orelse return;
    const active_id = tl_context_id;
    const msg = ct.pool_dequeue(pd) orelse return;
    switch (msg) {
        .ctx_resolve_call => |p| {
            if (p.context_id == active_id) state.resolve_pending(p.id, p.json)
            else handle_ctx_resolve_call(contexts, p);
        },
        // ... reject / resolve_term / send_message / define / get_global same shape
        // Re-enqueue messages that can't be processed during a promise wait
        .ctx_eval, .ctx_load_bytecode, .ctx_call_fn, .ctx_reset,
        .ctx_memory_usage, .ctx_dom_op => ct.pool_enqueue(pd, msg),
        .create_context, .destroy_context, .stop => ct.pool_enqueue(pd, msg),
    }
}
```

**Flow:** do_eval starts → install_pump sets threadlocals + drain_fn → engine hits an await → QuickJS calls drain_fn → pump dequeues ONE pool message → own-context resolutions feed the pending map directly; other-context messages are forwarded to their queues; heavy verbs (eval/reset/dom…) are RE-ENQUEUED because running them inside a yield would re-enter the engine → uninstall_pump clears everything after completion.
**Invariant:** (1) The pump processes at most ONE message per invocation — recursion through the engine is forbidden. (2) Heavy verbs MUST be re-enqueued, never executed from a drain callback — that is the re-entrancy wall. (3) Threadlocals are set/cleared in strict pairs; a missing uninstall leaks stale pointers into the next eval on this thread. (4) Forwarded messages keep their payloads alive (envs/frees handled by each handler's not-found branch). This is the trick that lets ONE thread serve many awaiting contexts without OS-level preemption.
**Probe:** `grep -c 'pool_enqueue(pd, msg)' lib/quickbeam/context_worker.zig` → 2 (heavy-verb arm + control arm).
**Probe:** `grep -c 'install_pump' lib/quickbeam/context_worker.zig` → 8 (def, uninstall twin, 2 call sites ×2 lines).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-quickbeam", query: "pool_drain_callback install_pump", limit: 10 });
```
(rank-1: install_punt... install_pump :28-38 — verified live)

## Verdict
Adopt the drain-callback pattern for any single-threaded multi-tenant engine with host-side async completions; adapt which verbs are "heavy" for your engine; omit nothing here — the one-message-per-drain and re-enqueue rules are the correctness core. Coverage: context_worker.zig no_recorded_issue+metadata_match.
