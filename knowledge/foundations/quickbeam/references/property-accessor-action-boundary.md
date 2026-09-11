<!-- capsule-v2 -->
# property-accessor-action-boundary — How does property access return an explicit accessor action instead of running JavaScript inside a read, and how do primitives reach their intrinsic prototypes?

**Source:** QuickBEAM MIT `master@c21c0e315213d0801950aae48cccedb3051c32d8`; Codebase Memory `quickbeam`. **Question:** How do you classify property receivers (heap objects, primitives, callables) so a read never executes JS, while getters/setters still run through the interpreter's planned-call machinery?

## Receiver-classified property semantic seam
**Path/Symbol:** `lib/quickbeam/vm/runtime/property.ex` (234L): `@function_tags` (:17-24), `get_result` type (:26-28), `get/3` 14 clauses (:31-75), `missing_reference_property/4` (:77-90), `global_property/3` (:92-97), `put/4` (:103-108), `define/5` (:111-113), `define_accessor/6` (:116-131), `define_descriptor/4` (:134-136), `delete/3` (:139-141), `enumerable_keys/2` (:144-154), `assignable_keys/2` (:161-166), `has_property?/3` (:169-180), `intrinsic_property/3` (:224-232), `map_string_key/2` (:234-244). Consumers: `opcode/object.ex` `get/put` arms (:618-646), `interpreter.ex` ObjectAssign continuation (:583/:600/:619).
**Signature:** `get(term(), term(), State.t()) :: {:ok, term() | {:accessor, getter, Reference.t()}} | {:error, term()}`; `put(term(), term(), term(), State.t()) :: {:ok, State.t()} | {:error, {:invoke_setter, setter}} | {:error, term()}`.
**Data Shape:** Read result is a three-way union: `{:ok, value}`, `{:ok, {:accessor, getter, receiver}}` (an ACTION the interpreter must dispatch), or `{:error, reason}` (e.g. `:null_or_undefined_property_access`). Write result is `{:ok, State.t()}`, `{:error, {:invoke_setter, setter}}`, or `{:error, reason}`.

### Decisive source
```elixir
def get(%PromiseReference{}, key, execution) when is_binary(key),
  do: intrinsic_property(execution, "Promise", key)

def get(object, key, execution)
    when is_tuple(object) and is_binary(key) and elem(object, 0) in @function_tags,
    do: intrinsic_property(execution, "Function", key)

def get(object, "length", _execution) when is_binary(object),
  do: {:ok, Value.string_length(object)}

def get(_object, _key, _execution) when object in [nil, :undefined],
  do: {:error, :null_or_undefined_property_access}

defp intrinsic_property(execution, constructor_name, key) do
  with %Reference{} = constructor <- Map.get(execution.globals, constructor_name),
       {:ok, %Reference{} = prototype} <- Heap.get(execution, constructor, "prototype") do
    Heap.get(execution, prototype, key)
  else
    _missing -> {:ok, :undefined}
  end
end
```

**Flow:** an opcode (`get_field`/`get_array_el`/`put_field`) or a boundary continuation calls `Property.get/put` → the receiver is classified by pattern position: `%Reference{}` → `Heap.get` walk (with a global-object fallback for missing keys and a RegExp `exec`/`test` special case); `%PromiseReference{}` / `%RegExp{}` / function-tag tuple / binary / list / number → structural read or `intrinsic_property` lookup through the installed `globals["Function"|"String"|"Array"|"Number"|"Promise"].prototype`; `nil`/`:undefined` → typed error → a getter hit returns `{:accessor, getter, receiver}` and the opcode layer converts it to `{:invoke_getter, …}`; a setter hit on write returns `{:error, {:invoke_setter, setter}}` → the interpreter dispatches both through the SAME `dispatch_call` planned-call path used for ordinary calls, so accessors observe the current frame stack and exception boundaries.
**Invariant:** `Property.get/put` NEVER executes JavaScript — every callable it encounters is returned as an action tuple; the original receiver is carried inside the accessor action so `this` binding is exact; primitive lookups degrade to `{:ok, :undefined}` (not errors) when the intrinsic prototype is not installed.
**Probe:** `test/vm/runtime/property_test.exs` (64L) — accessor read returns `{:ok, {:accessor, ^getter, ^object}}` with the ORIGINAL receiver and put returns `{:error, {:invoke_setter, ^setter}}`; intrinsic arms resolve `bind`/`name` on a builtin callable and `toString` on `42` as callable References; `"😀"` length/index reads.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "quickbeam", query: "Property.get accessor invoke_getter invoke_setter intrinsic_property function_tags receiver", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three-way read union with the accessor action — it is the property-side twin of the plan-don't-execute call classifier and is what keeps the interpreter the only JS executor. Adopt receiver-classified clauses for primitives with `intrinsic_property` degrading to `:undefined`. Adapt the `@function_tags` list to your callable representation and the global-object fallback to your globals map. Omit `map_string_key/2`'s atom-key coercion if your primitive maps never use atom keys. Caveat: direct-read fallback (Codebase Memory MCP not connected this session); the RegExp `exec`/`test` special case is covered only indirectly (no dedicated regexp test read this pass).
