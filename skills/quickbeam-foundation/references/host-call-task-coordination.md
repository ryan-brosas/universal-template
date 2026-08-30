<!-- capsule-v2 -->
# host-call-task-coordination — How do you call a BEAM handler from JS without blocking the evaluation, and how do you prevent handler leaks when the evaluation dies?

**Source:** QuickBEAM MIT `master@c21c0e315213d0801950aae48cccedb3051c32d8`; Codebase Memory `quickbeam`. **Question:** What supervision shape lets `Beam.call` return a Promise immediately, settle it when a BEAM handler replies, and guarantee the handler dies with (or before) its evaluation?

## Owner-monitored host-call task seam
**Path/Symbol:** `lib/quickbeam/vm/runtime/async.ex`: `start_host_call/2` (:266-283), `start_handler_task/4` (:325-338), `coordinate_handler/4` (:340-355), `invoke_handler/2` (:357-365), `settle_host_reply/3` (:234-247), `cancel_operations/1` (:249-259), `@max_host_operations 64` (:23). Reply routing: the eval drive loop matches `{:quickbeam_vm_host_reply, operation, result}` (capsule vm-event-loop-drive).
**Signature:** `start_host_call([name | args], State.t()) :: {:ok, PromiseReference.t(), State.t()} | {:error, term(), State.t()}`; `settle_host_reply(State.t(), reference(), result) :: {:ok, State.t()} | :stale`.
**Data Shape:** `%State{}.operations` maps `make_ref()` → `{PromiseReference.t(), handler_pid}`; `%State{}.handlers` maps handler name → function (validated at eval start).

### Decisive source
```elixir
defp coordinate_handler(owner, operation, handler, arguments) do
  owner_monitor = Process.monitor(owner)
  coordinator = self()

  handler_pid =
    spawn_link(fn ->
      send(coordinator, {operation, invoke_handler(handler, arguments)})
    end)

  receive do
    {^operation, result} ->
      Process.demonitor(owner_monitor, [:flush])
      send(owner, {:quickbeam_vm_host_reply, operation, result})

    {:DOWN, ^owner_monitor, :process, ^owner, _reason} ->
      Process.exit(handler_pid, :kill)
  end
end
```

**Flow:** `Beam.call(name, ...)` → `start_host_call` checks `map_size(operations) < 64` (else `{:limit_exceeded, :host_operations, 64}`) → allocates an owner-local Promise → `Task.Supervisor.start_child(QuickBEAM.VM.TaskSupervisor, ...)` runs the coordinator → coordinator monitors the OWNER and `spawn_link`s the real handler → handler result comes back to the coordinator tagged with `operation` → coordinator sends `{:quickbeam_vm_host_reply, operation, result}` to the owner → the drive loop calls `settle_host_reply`, which pops the operation (unknown ref → `:stale`, dropped), charges the result's memory estimate, and settles the promise. Owner DOWN before reply → coordinator kills the handler — a dead evaluation cannot leak a live handler. Unknown handler name settles the promise `{:error, {:unknown_handler, name}}` (catchable in JS, not a crash). `cancel_operations/1` kills every live handler pid (eval end / unobserved calls). Handler raise/exit is captured by `invoke_handler` into `{:error, {:handler_exception, ...}}` so JS `catch` sees it.
**Invariant:** exactly one reply per `make_ref()` (second reply is `:stale`); every live handler is either linked to a coordinator that monitors a live owner or already killed; the outstanding-operation cap bounds process growth per evaluation; the evaluation process NEVER blocks on a handler.
**Probe:** `test/vm/runtime/async_test.exs` (143L) — non-blocking await (:6-17), independent slow/fast settlement (:19-39), `Promise.all` over concurrent `Beam.call`s (:41-58), handler raise → catchable (:60-73), unknown handler → catchable (:75-87), unobserved handler cancelled with DOWN observed under `isolation: :caller` (:89-105), wall-clock timeout → `{:limit_exceeded, :timeout, 5000}` + handler DOWN (:107-124), 65 calls → `{:limit_exceeded, :host_operations, 64}` (:126-131). Unit: `async_semantics_test.exs` `:stale` second reply + `memory_used > 0` after settle.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "quickbeam", query: "start_host_call coordinate_handler settle_host_reply max_host_operations", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three-process shape: Task.Supervisor child as coordinator (owner monitor + reply relay), spawn_link'd handler (crash propagation), owner-local promise keyed by `make_ref()` with stale-reply drops and a hard outstanding-ops cap. Adapt the supervisor name, reply message tag, and memory-charging to your host. Omit nothing behavioral — the owner-DOWN kill and the cap are the leak-prevention core. Caveats: the globalThis-side of handler registration is validated at eval start (`{:invalid_option, :handlers, ...}` for bad arities); wall-clock timeout is enforced by the eval driver, not the coordinator. Direct-read fallback: whole-file async.ex + async_test.exs whole reads + probe census (@max_host_operations/Task.Supervisor/Process.exit/quickbeam_vm_host_reply sites re-grepped ×7); no graph coverage check in-session.
