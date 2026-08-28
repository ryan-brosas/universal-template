<!-- capsule-v2 -->
# promise-resolution-state-machine — How do you implement the ECMA-262 Promise resolution procedure (adoption, thenable assimilation, synchronous getter reads, FIFO jobs) with no threads and no microtask-queue process?

**Source:** QuickBEAM MIT `master@c21c0e315213d0801950aae48cccedb3051c32d8`; Codebase Memory `quickbeam`. **Question:** Where does Promise state live when the whole evaluation is one process, and how do adoption/thenable semantics stay spec-correct without spawning anything?

## Owner-local resolution-procedure seam
**Path/Symbol:** `lib/quickbeam/vm/runtime/promise.ex` (450L): `new/1` (:23-37), `state/2` (:39-45, maps internal `:resolving` → observable `:pending`), `await/3` (:47-56), `react/4` (:59-75), `aggregate/3` + `aggregate_into/4` (:77-121, `make_ref()`-keyed maps with a `remaining` counter), `settle_aggregate/4` (:123-149), `finally/3` (:151-163), `attach_reaction/4` (:165-174), `settle_after_finally/4` (:176-186), `settle/3` clauses (:194-248), `settle_assimilated/3` (:256-263), `fulfill_assimilated/3` (:269-275), `settle_result/3` (:280-299), `then_callable/2` (:301-324), `add_waiter/3` (:427-429), `enqueue_waiter/3` clauses (:431-443), `enqueue/2` + `enqueue_sync/2` (:445-449). State fields: `state.ex` `promises`/`promise_waiters`/`promise_aggregates`/`jobs`/`sync_jobs`/`sync_jobs_pending?` (:24-39). Sync drain: `interpreter.ex` `run_synchronous_job/1` (:180-188), `run/2` head drain (:280-289), `continue_iterator_sync/2` (:542-553), `put_sync_jobs/2` (:784-785).
**Signature:** `settle(State.t(), PromiseReference.t(), {:ok, term()} | {:error, term()}) :: State.t()`; `new(State.t()) :: {PromiseReference.t(), State.t()}`.
**Data Shape:** `%State{}.promises` maps `id → :pending | :resolving | {:fulfilled, v} | {:rejected, r}`; `%State{}.promise_waiters` maps `id → [waiter]` where a waiter is a `%Coroutine{}`, `%Reaction{}`, `{:adopt, target}`, `{:finally_adopt, target, original_result}`, or `{:aggregate, ref, index}`; waiters are consed (LIFO storage) then `Enum.reverse`d at settle so jobs enqueue in FIFO insertion order.

### Decisive source
```elixir
def settle(execution, %PromiseReference{id: id} = promise, {:ok, %PromiseReference{id: id}}),
  do: settle(execution, promise, {:error, {:type_error, :promise_self_resolution}})

def settle(execution, %PromiseReference{id: id} = promise, {:ok, %PromiseReference{} = source}) do
  case Map.fetch!(execution.promises, id) do
    :pending ->
      case state(execution, source) do
        :pending ->
          execution = %{execution | promises: Map.put(execution.promises, id, :resolving)}
          add_waiter(execution, source.id, {:adopt, promise})
        {:fulfilled, value} -> settle(execution, promise, {:ok, value})
        {:rejected, reason} -> settle(execution, promise, {:error, reason})
      end
    _settled_or_resolving -> execution
  end
end

def settle(execution, %PromiseReference{id: id} = promise, {:ok, %Reference{} = value} = result) do
  case Map.fetch!(execution.promises, id) do
    :pending ->
      case then_callable(execution, value) do
        {:ok, callable} ->
          execution = %{execution | promises: Map.put(execution.promises, id, :resolving)}
          enqueue(execution, {:assimilate_thenable, promise, value, callable})
        {:getter, getter, receiver} ->
          execution = %{execution | promises: Map.put(execution.promises, id, :resolving)}
          enqueue_sync(execution, {:read_thenable, promise, receiver, getter})
        :none -> settle_result(execution, promise, result)
      end
    _settled_or_resolving -> execution
  end
end
```

**Flow:** resolve value → self-resolution clause first (TypeError) → Promise value: mark `:resolving`, park an `{:adopt, target}` waiter on the source, `settle_assimilated/3` later unlocks (`:resolving → :pending → settle`) → thenable value: callable `then` becomes a normal async job (`enqueue`), accessor `then` MUST be read synchronously per spec so it goes on the separate `sync_jobs` queue (`enqueue_sync` sets `sync_jobs_pending?`), and `run/2` drains sync jobs at the top of every step → plain value: `settle_result` pops waiters, reverses, enqueues one job per waiter. `finally` waiters (`{:finally_adopt, target, original_result}`) settle the target with the ORIGINAL result regardless of callback outcome; a callback-returned Promise is awaited first (`complete_reaction` mode `:finally` → `settle_after_finally`). Aggregates: `make_ref()` key + `remaining` counter; `race`/`any` settle on first event and delete; `all` rejects fast; `any` collects unwrapped reasons into a synthetic `%{"name" => "AggregateError", ...}` map.
**Invariant:** a promise settles exactly once (`:resolving` and settled states are no-op clauses); getter-`then` is read before any other job can run; waiter jobs enqueue in insertion order; every job mutates only the owner-local `%State{}` — no process is ever spawned.
**Probe:** `test/vm/runtime/promise_test.exs` (211L) — native-parity harness `assert_vm_matches_native/2` (:204-210) runs each source through BOTH the QuickJS runtime and the compiled interpreter and asserts equal results; pins FIFO microtask order (`"ab"` :112-127), nested-detach order (`"abc"` :128-143), synchronous accessor reads (`order === "abc"` ordering test :96-110), self-resolution → `"TypeError"` (:169-181), `finally` preserving completion (:156-167), and `max_stack_depth: 1` still evaluating a detached reaction (:183-186).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "quickbeam", query: "settle_assimilated finally_adopt promise_self_resolution enqueue_sync", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the owner-local state-machine shape: promise states + waiters + jobs as plain maps/queues in one explicit state struct, `:resolving` as an internal lock during adoption, sync-vs-async job queues for the getter/callable `then` split, and reverse-on-settle FIFO. Adapt the job queue to your host (here `:queue` drained by one interpreter loop; a port needs an equivalent single-threaded pump, not per-promise processes). Omit nothing behavioral — but note the caveat that `state/2` deliberately hides `:resolving` from observers, so external code must never branch on it. Direct-read fallback: evidence chain is whole-file source + test reads + byte-for-byte probes (def census ×46, `:resolving` ×6, self-resolution/enqueue_sync/AggregateError sites re-grepped this pass); no graph coverage check was possible in-session.
