<!-- capsule-v2 -->
# iterator-protocol-resumable-phases — How do you run the iterator protocol for Promise combinators without ever calling JavaScript recursively?

**Source:** QuickBEAM MIT `master@c21c0e315213d0801950aae48cccedb3051c32d8`; Codebase Memory `quickbeam`. **Question:** How do you consume `[Symbol.iterator]`, `next`, `done`, and `value` — each of which may be a getter or a function that runs arbitrary JS — as a resumable state machine instead of a recursive call?

## Six-phase resumable iterator seam
**Path/Symbol:** `lib/quickbeam/vm/runtime/iterator.ex` (253L): `values/2` immediate-collection clauses (:29-57), `start/5` (:61-75), `start_set/5` (:79-90), `resume/3` six phase clauses (:94-120), `continue/2` (:124-125), `reject/3` (:129-133), `fail/3` (:137-138), private ladder `read_iterator_method` → `invoke_iterator_factory` → `read_next` → `invoke_next` → `next_iteration` → `read_done` → `after_done` → `finish` → `read_value` (:140-228). Boundary struct: `lib/quickbeam/vm/runtime/boundary/iterator.ex` (44L, `phase` type :21-27). Interpreter wiring: `interpreter.ex:446-449` (`{:promise_iterate, ...}` → `Iterator.start`), `:470-477` (`{:iterator_value, ...}` consumers), `complete_call_result` on `%Boundary.Iterator{}` → `Iterator.resume` (:479-481), `:1058` (return_value resume).
**Signature:** `values(term(), State.t()) :: {:ok, [term()]} | {:resumable} | {:error, :not_iterable}`; `start(kind, iterable, caller, execution, tail?) :: action()`; `resume(value, Boundary.Iterator.t(), State.t()) :: action()`.
**Data Shape:** `%Boundary.Iterator{consumer: :promise | :set, kind: :all | :all_settled | :any | :race | nil, promise, target, iterable, iterator, next, result, phase, caller, depth, values: [], tail?}` — the boundary IS the loop state; `phase` names which JS invocation is in flight.

### Decisive source
```elixir
def resume(result, %Boundary.Iterator{phase: :next_call} = boundary, execution) do
  if object?(result) do
    read_done(%{boundary | result: result, phase: nil}, execution)
  else
    reject(boundary, {:type_error, :iterator_result_not_object}, execution)
  end
end

defp finish(%Boundary.Iterator{consumer: :promise} = boundary, execution) do
  values = Enum.reverse(boundary.values)
  execution = Promise.aggregate_into(execution, boundary.promise, boundary.kind, values)
  complete(boundary, execution)
end

defp dispatch(boundary, phase, callable, arguments, this, execution),
  do: {:dispatch, callable, arguments, this, %{boundary | phase: phase}, execution, false}
```

**Flow:** `Promise.all/settled/any/race` builtins call `Iterator.values/2` first — lists, binaries (codepoints), arrays (holes → `:undefined`), maps (entries as `[key, value]` pairs), and sets collect immediately with zero JS calls; a plain object returns `{:resumable}` and the builtin emits `{:promise_iterate, kind, iterable, ...}` → `Iterator.start/5` allocates the result promise, wraps the caller in a `%Boundary.Iterator{consumer: :promise, phase: nil}`, and reads `Symbol.iterator` → getter? dispatch as `:iterator_getter` → factory callable? dispatch as `:iterator_factory` → result object? read `next` → getter `:next_getter` / callable `:next_call` → result object? (else `:iterator_result_not_object`) read `done` → getter `:done_getter` → truthy? finish : read `value` → getter `:value_getter` → `{:iterator_value, value, boundary, execution}` → interpreter pushes the value (Promise consumers wrap it via `Promise.from_value` so thenables assimilate) and calls `Iterator.continue/2` for the next round. Every JS invocation is a `{:dispatch, ...}` action with the phase stamped on the boundary; the interpreter's completion path routes the result back to `Iterator.resume/3` by boundary type. Set construction mirrors this with `consumer: :set` and finishes as `{:initialize_set, target, values, ...}`. Any property error or non-callable rejects via `reject/3` — promise consumers settle the combinator promise (`Exception.materialize` first), set consumers rethrow to the constructor caller.
**Invariant:** no JS call is ever executed inside iterator.ex — the module only plans dispatches and consumes their results through `resume/3`; the accumulated `values` list is built head-first and reversed exactly once at finish; `depth` is captured at start so unwinding restores it.
**Probe:** `test/vm/runtime/promise_test.exs:77-95` — native-parity sources cover: manual iterator object, function-valued `Symbol.iterator`, accessor getter (read-count pinned to 1), getter that throws (41), factory that throws (42), accessor `next`, `next` that throws, `done` getter that throws, `value` getter that throws, and `return()` close after a throwing `next`. `test/vm/runtime/opcode_test.exs` header notes resumable frames; opcode-level spread/for-of DEGRADE on `{:resumable}` (`opcode/object.ex:375-376` `:unsupported_resumable_spread`, `:455-456` `:unsupported_resumable_for_of`) — only the Promise-combinator lane is resumable.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "quickbeam", query: "Boundary.Iterator phase iterator_getter next_call done_getter value_getter resumable", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the boundary-as-loop-state pattern: stamp the protocol phase on a struct pushed into the caller list, dispatch each JS-touching step as an action, and route completions back by boundary type — this is the general recipe for any multi-step JS protocol (spread, destructuring, for-await). Adopt immediate collection for the fast shapes (list/binary/array/map/set) to keep the common path synchronous. Adapt the phase set to your protocol; the `iterator_result_not_object` checks and holes→undefined array mapping are spec-shaped. Omit the Set-consumer arm if you have no Set constructor. Caveats: direct-read fallback; the iterator `return()` close protocol appears in native-parity test sources but is NOT implemented in iterator.ex (recorded as an observed gap, not a seam); no dedicated iterator_test.exs exists — coverage is via promise_test native parity.
