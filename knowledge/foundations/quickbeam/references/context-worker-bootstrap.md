<!-- capsule-v2 -->
# context-worker-bootstrap — How do you fake Web Workers when the host already has cheap isolated contexts?

**Source:** QuickBEAM MIT `master@c21c0e31`; Codebase Memory `ext-quickbeam`. **Question:** What is the minimal Worker emulation — spawn, postMessage, onmessage, terminate — over a context pool?

## Worker-as-child-Context seam
**Path/Symbol:** `lib/quickbeam/context.ex:@worker_bootstrap` (:466-477), `handle_worker_call(:spawn|:terminate|:post_to_child)` (:479-571), worker message plumbing `handle_info({:worker_started,...}/{:worker_msg,...}/{:worker_error,...})` (:387-414); Runtime twin at runtime.ex :637-675 keyed by worker_id.
**Signature:** JS surface: `postMessage(data)` → `Beam.call("__worker_post", data)`; `onmessage = h` via setter trap → `Beam.onMessage(msg => handler({data: msg}))`. Handler map for child: `%{"__worker_post" => fn [data] -> send(parent_pid, {:worker_msg, worker_id, data}); nil end}`.
**Data Shape:** Child Context started with `apis: false` (bare engine) on the SAME pool; parent tracks `{ref→{child_pid, worker_id}}` in state.workers.

### Decisive source
```elixir
Task.start(fn ->
  {:ok, child} = QuickBEAM.Context.start_link(pool: pool, apis: false,
      handlers: %{"__worker_post" => fn [data] ->
        send(parent_pid, {:worker_msg, worker_id, data}); nil end})
  send(parent_pid, {:worker_started, worker_id, child})
  QuickBEAM.Context.eval(child, @worker_bootstrap)
  case QuickBEAM.Context.eval(child, script) do
    {:ok, _} -> :ok
    {:error, err} -> send(parent_pid, {:worker_error, worker_id, err})
  end
end)
QuickBEAM.Native.pool_resolve_call_term(resource, state.context_id, call_id, worker_id)
```

**Flow:** JS calls Worker(url) → __worker_spawn handler resolves the constructor call IMMEDIATELY with a synthetic id (spawn is async by contract) → Task creates bare child context → bootstrap defines self/postMessage/onmessage-setter → script evaluated; errors travel as {:worker_error,...} → parent forwards to its own JS as ["__worker_msg"/"__worker_err", worker_id, data] messages.
**Invariant:** (1) The bootstrap's onmessage SETTER TRAP converts property assignment into a Beam.onMessage subscription — plain assignment without it would overwrite instead of register. (2) Child gets NO apis (`apis: false`) — workers don't inherit DOM/fetch unless explicitly added. (3) spawn resolves BEFORE the child exists: worker scripts that postMessage during load still work because messages route through the parent mailbox. (4) Terminate demonitors then stops asynchronously in a Task so a dying child can't deadlock the handler. (5) The Runtime twin implements the same three verbs with different transport (direct Native.send_message vs pool_*), proving the seam is transport-independent.
**Probe:** `grep -c 'worker_bootstrap' lib/quickbeam/context.ex` → 2 (attr + use).
**Probe:** `grep -c '__worker_msg' lib/quickbeam/runtime.ex lib/quickbeam/context.ex` → 1 and 1.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-quickbeam", query: "worker bootstrap onmessage postMessage", limit: 10 });
```

## Verdict
Adopt Worker-over-cheap-sandbox emulation (bare context + setter-trap bootstrap + async id resolution); adapt message envelope tags; omit dedicated-thread fidelity if your users don't need true parallelism inside workers. Coverage: context.ex no_recorded_issue; exercised by test/core/context_pool_test.exs worker sections.
