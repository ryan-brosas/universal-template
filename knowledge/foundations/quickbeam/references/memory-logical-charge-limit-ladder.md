<!-- capsule-v2 -->
# memory-logical-charge-limit-ladder — How do you bound JavaScript allocation with deterministic logical accounting that JS catch handlers cannot intercept, backed by a real process-heap kill switch?

**Source:** QuickBEAM MIT `master@c21c0e315213d0801950aae48cccedb3051c32d8`; Codebase Memory `quickbeam`. **Question:** How do you enforce a memory budget over untrusted JS without a garbage collector, so exhaustion is a typed error the guest cannot catch and the host process cannot actually OOM?

## Logical charge → latch → typed-error → max_heap kill seam
**Path/Symbol:** `lib/quickbeam/vm/runtime/memory.ex` (92L): `@object_bytes 128` / `@property_bytes 64` / `@cell_bytes 32` / `@promise_bytes 64` (:13-16), `charge/2` (:19-27), `charge_object/charge_property/charge_cell/charge_promise` (:30-37), `estimate/1` 12 clauses (:40-63, `%Object{}` → `464 + …`). Latch gates: `interpreter.ex:103-104` (invoke_global), `interpreter.ex:291-292` (run loop). Charges at allocation sites: `heap.ex` `store_new_object`/`store_default_array_index`/`maybe_charge_property` (7 `charge_property` sites), `interpreter.ex:84/:101/:915`. Engine ladder: `engine.ex:20` (`@default_memory_limit 64 * 1024 * 1024`), `:195` validation, `:287-288` spawn, `worker_spawn_options/1` (:391-401), `evaluation_exit(:killed, memory_limit)` (:432).
**Signature:** `charge(State.t(), non_neg_integer()) :: State.t()`; `estimate(term()) :: non_neg_integer()`.
**Data Shape:** `State.memory_used` (monotonic counter), `State.memory_exceeded` (sticky boolean latch), `State.memory_limit` (`:infinity` | positive integer). Failure shape is always `{:error, {:limit_exceeded, :memory_bytes, limit}, execution}`.

### Decisive source
```elixir
def charge(%State{} = execution, bytes) when is_integer(bytes) and bytes >= 0 do
  used = execution.memory_used + bytes

  exceeded =
    execution.memory_exceeded or
      (execution.memory_limit != :infinity and used > execution.memory_limit)

  %{execution | memory_used: used, memory_exceeded: exceeded}
end

defp run(_frame, %State{memory_exceeded: true} = execution),
  do: {:error, {:limit_exceeded, :memory_bytes, execution.memory_limit}, execution}

defp worker_spawn_options(memory_limit) do
  word_size = :erlang.system_info(:wordsize)
  max_heap_words = div(memory_limit + @worker_heap_overhead + word_size - 1, word_size)

  [:monitor, {:max_heap_size, %{size: max_heap_words, kill: true, error_logger: false}}]
end

defp evaluation_exit(:killed, memory_limit) when is_integer(memory_limit),
  do: {:error, {:limit_exceeded, :memory_bytes, memory_limit}}
```

**Flow:** every allocation site charges BEFORE storing (`Heap.allocate` → `charge_object`; new property → `charge_property`; captured cell → `charge_cell`; promise record → `charge_promise`; initial vars/arguments and template adoption → `Memory.charge(execution, Memory.estimate(...))`) → `charge/2` adds a deterministic estimate and latches `memory_exceeded` when the limit is crossed (the allocation itself still completes — the latch is checked at control points) → the interpreter run loop and `invoke_global` check the latch FIRST, returning the typed `{:limit_exceeded, :memory_bytes, limit}` error that flows through the normal error path — indistinguishable from a thrown error to the host but NOT catchable by guest `try/catch` because it never enters the throw machinery → in isolated mode the same limit is converted to BEAM `max_heap_size` words on the worker spawn, so a guest that escapes logical accounting (e.g. a huge host result) is killed by the VM and the DOWN reason `:killed` maps back to the identical typed error → option validation rejects `0`, negatives, and non-integers (`{:invalid_option, :memory_limit, value}`).
**Invariant:** accounting is deterministic and monotonic (same program + inputs → same `memory_used`; no GC credit until implemented); the latch is sticky — once exceeded, every subsequent check fails; the guest can never observe or catch the memory error; the logical estimate is always backed by a hard process-level ceiling in isolated mode.
**Probe:** `test/vm/memory_limit_test.exs` (69L) — `Memory.estimate(%Object{}) == 520` pins the canonical estimate; invalid limits `0/-1/"1 MB"` → `{:invalid_option, :memory_limit, …}`; 1 000-object loop under limit 20 000 → `{:limit_exceeded, :memory_bytes, 20_000}` in BOTH `:caller` and `:process` isolation; `try { while(true) … } catch` still yields the limit error (catch-interception impossible); oversized host result → handler process and evaluation owner both dead (`refute Process.alive?`) with the same typed error.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "quickbeam", query: "Memory.charge estimate memory_exceeded memory_limit limit_exceeded memory_bytes max_heap_size worker_spawn_options", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt charge-before-store with a sticky latch checked at loop control points — it gives deterministic, catch-proof budget enforcement without a GC. Adopt the dual ladder (logical estimate + BEAM `max_heap_size` kill with `:killed` → typed-error mapping) whenever guest code can influence host-side allocation (host results, handler payloads). Adapt the byte constants (128/64/32/64 + per-value estimates) to your value representation — they are calibrated to this VM's term shapes, not universal. Omit the estimate recursion over maps/tuples only if your host charges at a coarser granularity. Caveat: direct-read fallback (Codebase Memory MCP not connected this session); `@worker_heap_overhead`'s exact value is cited from engine.ex context but not probed numerically this pass.
