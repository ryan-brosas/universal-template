<!-- capsule-v2 -->
# invocation-call-classifier-actions — How do you classify every JavaScript call shape into explicit interpreter actions without recursive execution?

**Source:** QuickBEAM MIT `master@c21c0e315213d0801950aae48cccedb3051c32d8`; Codebase Memory `quickbeam`. **Question:** How does a pure-Elixir JS engine turn "call this value" into a closed set of actions the interpreter can schedule, so no call path ever re-enters the interpreter recursively?

## Plan-don't-execute call seam
**Path/Symbol:** `lib/quickbeam/vm/runtime/invocation.ex` (229L): `plan/6` 10 clauses (:42-135), `action()` type (:27-38), `@builtin_tags` (:25), `new_frame/5` (:195-210), `enter_action/7` (:212-221), `callable_parts/1` (:223-228). Interpreter consumer: `interpreter.ex:398` (`dispatch_call` → `Invocation.plan` → `execute_invocation` :402-477).
**Signature:** `plan(callable, arguments, this, caller, execution, tail? \\ false) :: action()` where `action()` ∈ `{:dispatch, ...} | {:enter, ...} | {:complete, ...} | {:error, ...} | {:host_call, ...} | {:object_assign, ...} | {:array_iteration, ...} | {:promise_iterate, ...} | {:set_iterate, ...} | {:iterator_value, ...}`.
**Data Shape:** callable terms: `{:host_function, :beam_call}`, `{:declared_builtin, module, handler}`, `{:promise_resolver, promise, kind}`, `{:bound_function, target, this, args}`, `%Reference{}` (heap object), `{:primitive_method, :array, method}`, builtin tuples tagged `:builtin | :declared_builtin | :primitive_method`, `%Function{}`, `{:closure, function, refs}`. The `caller` term is itself a boundary struct or frame — plan threads it verbatim into the action.

### Decisive source
```elixir
def plan({:host_function, :beam_call}, arguments, _this, caller, execution, tail?),
  do: {:host_call, arguments, caller, execution, tail?}

def plan({:promise_resolver, promise, kind}, arguments, _this, caller, execution, tail?) do
  value = Enum.at(arguments, 0, :undefined)
  result = if kind in [:resolve, :resolve_assimilated], do: {:ok, value}, else: {:error, value}
  execution =
    if kind in [:resolve_assimilated, :reject_assimilated],
      do: Promise.settle_assimilated(execution, promise, result),
      else: Promise.settle(execution, promise, result)
  {:complete, :undefined, caller, execution, tail?}
end

def plan(
      {:bound_function, target, bound_this, bound_arguments},
      arguments,
      _this,
      caller,
      execution,
      tail?
    ),
    do: {:dispatch, target, bound_arguments ++ arguments, bound_this, caller, execution, tail?}
```

**Flow:** opcode `:call`/`:call_method`/`:apply` (opcode/invocation.ex) builds `{:invoke, callable, args, this, caller, ...}` → interpreter `execute_opcode({:invoke, ...})` → `dispatch_call` → `Invocation.plan/6` classifies → `execute_invocation/1` loops the action back through `dispatch_call` (for `:dispatch`), `enter_planned_call` (for `:enter`, which splits sync vs async by `func_kind == 2`), `complete_call_result`, `raise_js_from_caller`, `start_host_call`, or the iterator/object-assign starters. Promise resolvers settle inline inside `plan` and return `{:complete, :undefined, ...}` — the resolver call itself produces no value. `new_frame/5` pads missing args with `:undefined` to `arg_count` and sizes locals as `max(arg_count + var_count, 1)`.
**Invariant:** `plan/6` never runs interpreter frames — it only mutates `execution` through settled side-effecting calls (resolvers, builtins) and returns data. Every recursive-looking path is re-expressed as a returned action the interpreter's single `execute_invocation` reducer consumes, so the BEAM stack depth is bounded by the reducer loop, not by JS call depth.
**Probe:** `test/vm/runtime/invocation_test.exs` (88L) — `{:enter, ^function, ^function, {}, [7], :receiver, ^caller, ^execution, false}` for ordinary calls; closure enter carries `{:cell}` refs and `callable` = the closure tuple; `new_frame` locals tuple_size == 3 for arg_count 1 + var_count 2; bound-function dispatch prepends bound args `[1, 2]` and selects `:bound_receiver` (normal) vs `:instance` (under `%Boundary.Constructor{}`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "quickbeam", query: "Invocation.plan dispatch enter complete host_call action classifier", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the plan-don't-execute split: one total classifier from callable shape to a closed action union, consumed by a single interpreter reducer — this is what makes the owner-local event loop and depth accounting tractable. Adapt the action union to your opcode set; the promise-resolver-inline-settle and bound-function receiver rules (constructor caller keeps the instance as `this`) are JS-spec-shaped and port as-is. Omit the `{:host_function, :beam_call}` arm if your host has no BEAM handler surface. Caveat: direct-read fallback (MCP not connected in-session); coverage for invocation.ex is indirect via invocation_test.exs + interpreter suites.
