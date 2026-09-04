<!-- capsule-v2 -->
# context-pool-single-thread-multicontext — How do you host thousands of JS sandboxes without thousands of threads?

**Source:** QuickBEAM MIT `master@c21c0e31`; Codebase Memory `ext-quickbeam`. **Question:** What is the two-level architecture that gives per-connection JS state at ~58 KB instead of ~2 MB+?

## ContextPool round-robin seam
**Path/Symbol:** `lib/quickbeam/context_pool.ex:init/2` (:47-70), `handle_call({:create_context,...})` (:72-99); thread side `lib/quickbeam/context_worker.zig:pool_worker_main` (:112-177); consumer `lib/quickbeam/context.ex:build_state` (:155-171).
**Signature:** `start_link(opts)` `:size` default `System.schedulers_online()`; `create_context(pool, owner_pid, opts) :: {resource, context_id}`; per-context opts only `:memory_limit` (default 0 = unlimited) and `:max_reductions`.
**Data Shape:** GenServer owns a TUPLE of pool resources (one native thread each); each context = integer id + owner pid; contexts are ~58 KB bare to ~429 KB with full browser APIs vs ~2 MB+ runtime threads.

### Decisive source
```elixir
thread_idx = rem(state.next_thread, tuple_size(state.threads))
resource   = elem(state.threads, thread_idx)
ref = QuickBEAM.Native.pool_create_context(resource, context_id, owner_pid,
        memory_limit, max_reductions)
receive do
  {^ref, {:ok, ^context_id}} ->
    {:reply, {resource, context_id}, %{state | next_id: context_id + 1,
                                               next_thread: thread_idx + 1}}
  {^ref, {:error, reason}} -> {:reply, {:error, reason}, state}
after
  30_000 -> {:reply, {:error, :timeout}, state}
end
```

**Flow:** Context.start_link → GenServer.create_context → round-robin thread pick → NIF enqueues create on that thread's queue → thread builds JSContext under its shared JSRuntime, registers rd in rd_map, replies with id → Context GenServer holds `{pool_resource, context_id}` and routes every eval/call through `Native.pool_*` verbs.
**Invariant:** (1) Contexts on ONE thread share that thread's memory_limit and execute SERIALLY — one context's infinite loop blocks its thread-mates unless bounded by timeout/reductions; placement is naive round-robin with no load balancing. (2) The GenServer synchronously waits for the thread's reply — creation backpressure surfaces as :timeout after 30 s. (3) Per-context heap caps require explicit opt-in (`memory_limit > 0` gates `JS_SetContextMemoryLimit`); reduction limit likewise. (4) Owner pid is baked into the context entry so the LINK semantics of start_link give free cleanup: LiveView process death ⇒ terminate ⇒ pool_destroy_context.
**Probe:** `grep -c 'rem(state.next_thread' lib/quickbeam/context_pool.ex` → 1.
**Probe:** `grep -c 'max_reductions' lib/quickbeam/context_worker.zig` → 3.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-quickbeam", query: "pool_worker_main create_context round robin threads", limit: 10 });
```

## Verdict
Adopt the two-level design (few engine threads × many cheap contexts) for per-connection sandboxes; adapt sizing defaults and add real load balancing if your workloads skew; omit the reduction-limit knob if your engine lacks an opcode budget. Coverage: both cited paths no_recorded_issue+metadata_match; direct test test/core/context_pool_test.exs (376 lines) executes isolation/reset/handler seams at the pin.
