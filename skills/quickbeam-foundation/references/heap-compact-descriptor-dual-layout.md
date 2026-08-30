<!-- capsule-v2 -->
# heap-compact-descriptor-dual-layout — How do you store object properties so the common case is one tuple but accessor/descriptor semantics stay exact, with ECMAScript key ordering and array semantics?

**Source:** QuickBEAM MIT `master@c21c0e315213d0801950aae48cccedb3051c32d8`; Codebase Memory `quickbeam`. **Question:** How do you keep per-property storage cheap for default data properties while preserving full descriptor semantics (accessors, flags, non-configurable invariants), ECMAScript key order, and array length/hole behavior?

## Dual-layout object store seam
**Path/Symbol:** `lib/quickbeam/vm/runtime/heap.ex` (846L): `allocate/3` (:27-45), `allocate_array/2` (:48-64), `get/3` + `get_with_depth` (:116-119, :355-384), `has_property?/3` (:121-135), `put/4` (:138-158), `define/5` (:161-181), `own_property/3` (:184-204), `set_prototype/3` (:207-219), `define_accessor/6` (:232-257), `define_descriptor/4` (:260-271), `delete/3` (:274-291), `own_property_names/2` (:307-322), `own_keys/2` (:325-341), `valid_prototype?/3` + `prototype_contains?/4` (:343-364, `@max_prototype_depth 1_000` :15), `put_value/3` array-length arm (:564-571), `writable_descriptor/3` (:578-585), `validate_definition/3` + `validate_fixed_definition/5` (:641-680), `resize_array/2` (:790-803), `normalize_key/1` 7 clauses (:806-826), `remember_property/2` (:741-746). Struct: `object.ex` (`%Object{kind, prototype, properties, property_order, extensible, length, length_writable, callable, internal}`); `property/descriptor.ex` (`%Descriptor{kind, value, writable, enumerable, configurable, getter, setter}`). Export boundary: `value/export.ex` (107L, `convert/3` seen-map cycle rejection :29-40, `{:cyclic_result, id}`).
**Signature:** `get(State.t(), Reference.t(), term()) :: {:ok, term()} | {:error, term()}`; `put/define :: {:ok, State.t()} | {:error, term()}`; `own_keys :: {:ok, [term()]} | {:error, term()}`.
**Data Shape:** `%Object.properties` maps key → `{value}` (compact default data property: writable+enumerable+configurable, no accessors) OR `%Descriptor{}` (full form). `property_order` remembers insertion order of non-integer keys only. Array objects carry `length`/`length_writable` fields; holes are absent keys.

### Decisive source
```elixir
defp get_from_object(_execution, %Object{kind: :array, length: length}, "length", _receiver, _depth),
     do: {:ok, length}

defp get_from_object(execution, object, key, receiver, depth) do
  case Map.fetch(object.properties, key) do
    {:ok, {value}} -> {:ok, value}
    {:ok, %Descriptor{getter: getter}} when not is_nil(getter) ->
      {:ok, {:accessor, getter, receiver}}
    {:ok, %Descriptor{setter: setter}} when not is_nil(setter) -> {:ok, :undefined}
    {:ok, %Descriptor{value: value}} -> {:ok, value}
    :error -> get_from_prototype(execution, object.prototype, key, receiver, depth)
  end
end

defp put_property_struct(%Object{} = object, key, property) do
  if default_data_property?(property) do
    put_default_property(object, key, property.value)
  else
    object = remember_property(object, key)
    %{object | properties: Map.put(object.properties, key, property)}
  end
end
```

**Flow:** `Property.get(%Reference{})` → `Heap.get` → `get_with_depth` walks the prototype chain up to `@max_prototype_depth` (1 000; deeper → `{:error, :prototype_chain_too_deep}`) → per-object read matches the dual layout (compact tuple → value; accessor descriptor → action; setter-only → `:undefined`; data descriptor → value) → writes go through `put_value`/`validate_definition`: inherited non-writable/setter cases produce typed errors (`{:property_not_writable, key}`, `{:invoke_setter, setter}`, `{:object_not_extensible, key}`); non-configurable properties enforce the five `keep_*` redefinition rules → `put_property_struct` DOWNGRADES a descriptor back to `{value}` whenever it becomes a default data property → array writes track `length = max(length, key+1)`, `"length"` writes shrink via `resize_array` (rejecting non-configurable elements) and never materialize an enumerable length property → keys normalize through `normalize_key/1` (canonical array indices 0..2^32-2 stay integers; everything else becomes/keeps strings) → enumeration emits sorted integer keys then `property_order` string keys.
**Invariant:** the compact `{value}` form is EXACTLY equivalent to a default `%Descriptor{}` (helpers `Object.property_descriptor/1` and `property_enumerable?/1` are the only sanctioned readers); prototype reads carry the ORIGINAL receiver for accessor actions; cyclic prototype assignment is rejected (`:cyclic_prototype`) and cycle-safe export uses a seen-map (`{:cyclic_result, id}`) instead of infinite recursion.
**Probe:** `test/vm/runtime/heap_test.exs` (131L) — bulk `allocate_array` memory_used == sequential define-by-define accounting and identical objects; `properties["answer"] == {42}` compact assertion + `%Descriptor{value: "fixed", writable: false}` retained; sparse array `[:undefined, :undefined, "third"]` export; shrink-to-1 leaves `own_keys == [0]`; inherited non-writable write rejected; `[1, 4, "second", "first"]` key ordering; `{:ok, false, execution}` delete of non-configurable; `{:error, {:cyclic_result, object.id}}` self-reference export.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "quickbeam", query: "Heap.put validate_definition put_property_struct default_data_property own_keys normalize_key resize_array", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the dual compact/descriptor layout with sanctioned downgrade-on-default — it keeps the hot path (plain data property) to one Map lookup and one tuple while descriptor semantics stay lossless. Adopt the five non-configurable redefinition rules and the array shrink-with-nonconfigurable check. Adapt `@max_prototype_depth` and the seen-map export cycle policy to your host's limits. Omit `property_order` if your host tolerates unsorted string keys (ECMAScript order is observable via `Object.keys`). Caveat: direct-read fallback (Codebase Memory MCP not connected this session); `value/export.ex` is covered here via heap_test's cyclic_result probe rather than its own capsule.
