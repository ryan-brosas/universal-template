<!-- capsule-v2 -->
# exception-throw-unwind-catch-stack — How do thrown values stay JavaScript values inside the VM and become the public error struct only at the boundary, with async frames preserved?

**Source:** QuickBEAM MIT `master@c21c0e315213d0801950aae48cccedb3051c32d8`; Codebase Memory `quickbeam`. **Question:** How do you implement throw/catch over an explicit frame stack, unwind caller-by-caller across mixed frame/boundary callers, and keep the thrown value a heap reference until it escapes?

## Throw → catch-split → unwind → JSError seam
**Path/Symbol:** `lib/quickbeam/vm/runtime/exception.ex` (328L): `throw_at/3` (:35-44), `throw_from/3` (:47-51), `materialize/2` (:54-65), `to_js_error/3` (:68-79), `details/2` (:82-104), `throw_state/2` (:106-114), `do_throw/5` (:173-182), `unwind_caller/3` 12 clauses (:184-286), `stack_frame/2` (:288-300), `split_at_catch/1` (:317-322), `thrown/2` (:324). `:catch` marker push: `lib/quickbeam/vm/runtime/opcode/control.ex:49-50`. `Thrown` wrapper: `lib/quickbeam/vm/runtime/thrown.ex` (13L). Interpreter entry: `interpreter.ex:988-1003` (`raise_js`/`raise_js_from_caller` → `execute_exception`).
**Signature:** `throw_at(reason, Frame.t() | Frame.Native.t(), State.t()) :: action()`; `throw_from(reason, boundary, State.t()) :: action()`; `materialize(term(), State.t()) :: {term(), State.t()}`; `to_js_error(term(), State.t(), [JSError.frame()]) :: QuickBEAM.JSError.t()`.
**Data Shape:** `{:catch, target_pc}` markers live ON the frame value stack; `%Thrown{value, frames}` carries a raw thrown value plus preserved async frames while internal; `%QuickBEAM.JSError{name, message, filename, line, frames, stack}` is the public struct.

### Decisive source
```elixir
defp do_throw(reason, frame, execution, trace, caller?) do
  case split_at_catch(frame.stack) do
    {:caught, target, stack_below_catch} ->
      {:run, %{frame | pc: target, stack: [reason | stack_below_catch]}, execution}

    :uncaught ->
      trace = [stack_frame(frame, caller?) | trace]
      unwind_caller(reason, execution, trace)
  end
end

defp unwind_caller(reason, %State{callers: []} = execution, trace) do
  error = to_js_error(reason, execution, Enum.reverse(trace))
  {:error, error, execution}
end

defp split_at_catch(stack) do
  case Enum.split_while(stack, &(!match?({:catch, _target}, &1))) do
    {_discarded, [{:catch, target} | stack]} -> {:caught, target, stack}
    {_discarded, []} -> :uncaught
  end
end
```

**Flow:** `:catch` opcode pushes `{:catch, target}` onto the frame stack when entering a try block → a throw (`{:throw, reason, frame, execution}` from any opcode) routes to `Exception.throw_at/3` → `throw_state/2` materializes VM reason tuples (`{:type_error, _}` etc.) into heap error objects via `BuiltinRuntime.new_error` and unwraps a `%Thrown{}` to recover preserved async frames → `do_throw/5` splits the stack at the NEAREST `{:catch, marker}` (everything above it is discarded), sets `pc = target`, and pushes the raw reason as the catch operand → no marker: append the current frame's source-mapped position (`pc - 1` for caller frames, clamped to the instruction range) to the trace and pop one caller: `%Frame{}`/`%Native{}`/`%Boundary.ObjectAssign|Accessor|Constructor{}` re-throw into that caller (`depth` restored from `boundary.depth` or decremented), while protocol boundaries convert the throw into their domain outcome — `ThenGetter` → `settle_assimilated` + `{:resume_then_getter, ...}`, `Thenable`/`Reaction` → settle + `{:idle, ...}`, `PromiseExecutor`/`Iterator(promise)` → settle + `{:complete, promise, ...}`, `Iterator(set)` → rethrow into the constructor caller, `Async` → `Async.complete` + `{:async, ...}` → `callers == []`: `to_js_error/3` builds the public struct (heap Reference → `details/2` reads live `name`/`message` properties with internal-default fallbacks) and returns `{:error, error, execution}`.
**Invariant:** the thrown value stays a heap `%Reference{}` through every catch and unwind — conversion to `QuickBEAM.JSError` happens exactly once, at `callers == []`; async frames ride inside `%Thrown{}` and are prepended to the sync trace; the public stack never contains a BEAM/Elixir frame.
**Probe:** `test/vm/runtime/exception_test.exs` (98L) — catch-split resumes `pc == 7` with `stack == ["boom", :below]`; two-frame unwind yields `frames == ["current", "caller"]` and `depth == 1`; thenable/executor throws settle their promises as `{:rejected, %Thrown{value: ...}}`; async unwind returns `{:async, {:complete, promise, ...}}` with the async frame preserved and `callers == []`. `test/vm/runtime/error_test.exs:4-30` — end-to-end: `["inner", "outer", "<eval>"]` frames, source-mapped stack lines, `refute error.stack =~ "lib/quickbeam"`; :97-110 async handler failure keeps only `at load (async.js:1:)`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "quickbeam", query: "throw_at split_at_catch unwind_caller Thrown to_js_error JSError frames", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt catch-markers-on-the-value-stack (cheapest correct try model for a stack machine) and the convert-only-at-escape rule — it is what lets `catch (e) { e.name = ... }` observe live error objects. Adopt the boundary-tagged unwind clauses as the pattern for protocol-aware unwinding. Adapt `stack_frame`'s pc clamping and the `{:predefined, index}` atom-table name normalization to your function metadata. Omit `details/2`'s defensive non-string handling only if your host guarantees string properties. Caveat: direct-read fallback; `to_js_error` for `%Reference{}` whose object is not an error (`:error` branch) is covered only indirectly via error_test.
