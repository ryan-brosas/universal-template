<!-- capsule-v2 -->
# invocation-constructability-prototype — What makes a VM value constructable with `new`, and where does the instance's prototype come from?

**Source:** QuickBEAM MIT `master@c21c0e315213d0801950aae48cccedb3051c32d8`; Codebase Memory `quickbeam`. **Question:** How do you decide constructability and pick the allocation prototype for `new`/`super`/`instanceof` when callables may be heap references, closures, bound functions, or builtins?

## Constructability + prototype seam
**Path/Symbol:** `lib/quickbeam/vm/runtime/invocation.ex`: `constructable?/2` (:137-163), `constructor_prototype/2` (:165-175), `instanceof_prototype/2` (:177-183). Opcode consumers: `lib/quickbeam/vm/runtime/opcode/invocation.ex:63-64` (`:apply` with `constructor? == 1`), `:122-123` (`:init_ctor` super), `:142-143` (`:call_constructor`); `opcode/value.ex:135` (`instanceof`); `opcode/object.ex:600` (class extends check).
**Signature:** `constructable?(term(), State.t()) :: boolean()`; `constructor_prototype(term(), State.t()) :: Reference.t() | nil`; `instanceof_prototype(term(), State.t()) :: Property.get_result()`.
**Data Shape:** constructability ladder: heap `%Reference{}` → object must have `internal: :class_constructor`, else fall through to `BuiltinRuntime.callable/2` and recurse on the callable; `%Function{has_prototype: p}` → `p`; `{:closure, f, _}` → `f.has_prototype`; `{:bound_function, target, _, _}` → recurse on target; `{:declared_builtin, _, _}` → `Builtin.constructable?/1`; anything else → `false`.

### Decisive source
```elixir
def constructable?(%Reference{} = constructor, execution) do
  case Heap.fetch_object(execution, constructor) do
    {:ok, %{internal: :class_constructor}} ->
      true
    _other ->
      case BuiltinRuntime.callable(execution, constructor) do
        nil -> false
        callable -> constructable?(callable, execution)
      end
  end
end

def constructor_prototype(constructor, execution) do
  case Property.get(constructor, "prototype", execution) do
    {:ok, %Reference{} = prototype} -> prototype
    _other -> nil
  end
end
```

**Flow:** `:apply`/`:call_constructor` opcodes check `constructable?` first; on success they allocate `Heap.allocate(execution, :ordinary, prototype: constructor_prototype(...), internal: :constructor_instance)` and emit `{:invoke_constructor, ...}`; a `nil` prototype (constructor with non-object `prototype` property) is passed through and the object layer resolves it to the default. `:check_ctor` (opcode/invocation.ex:41-53) enforces that class constructors are only entered via `new` by verifying the `this` object carries `internal: :constructor_instance`, else throws `:class_constructor_requires_new`. `instanceof` uses `instanceof_prototype/2`, which deliberately does NOT unwrap bound functions' prototype differently — it recurses to the target and returns the raw `Property.get` result (including `{:error, _}`), unlike `constructor_prototype` which collapses failures to `nil`.
**Invariant:** constructability is a property of the callable chain, never of the call site; the instance marker `internal: :constructor_instance` is the single source of truth for "was constructed with new", and `constructor_prototype` reading the `prototype` PROPERTY (not a static field) is what makes `Constructor.prototype = {...}` reassignment affect subsequent allocations.
**Probe:** `test/vm/runtime/invocation_test.exs:46-57` — a heap-allocated function Reference with `has_prototype: true` plans `{:enter, ...}` with the Reference as callable and reports `typeof == "function"`, `constructable? == true`. `test/vm/runtime/error_test.exs:62-77` — `new RangeError("outside range")` then `throw error` yields `name == "RangeError"` and `error instanceof RangeError` in the hierarchy test (:79-92).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "quickbeam", query: "constructable constructor_prototype invoke_constructor class_constructor_requires_new check_ctor", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the constructability ladder and the property-read prototype (spec-shaped, cheap to port); adopt the `:constructor_instance` internal marker as the `new.target`-adjacent guard for class constructors. Adapt the recursion entry point to your builtin registry. Omit the `instanceof_prototype` error-passthrough nuance only if your `instanceof` already handles `{:error, _}`; note the two functions intentionally differ. Caveat: direct-read fallback; constructable? recursion on builtin-backed References is covered only indirectly via error_test/opcode suites.
