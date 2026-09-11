<!-- capsule-v2 -->
# opcode-value-semantic-action-adapter — How should value-family opcodes delegate semantics while preserving typed throws and prototype checks?

**Source:** QuickBEAM MIT `master@c21c0e315213d0801950aae48cccedb3051c32d8`; Codebase Memory `quickbeam` (not connected in-session — direct source/test fallback). **Question:** Where is the adapter boundary between decoded value opcodes and canonical value/property semantics?

## Value opcode adapter
**Path/Symbol:** `lib/quickbeam/vm/runtime/opcode/value.ex:1-133`, `execute/4`; interpreter dispatch `interpreter.ex:14585-14620`.
**Signature:** `execute(atom(), [term()], Frame.t(), State.t()) :: {:next, Frame.t(), State.t()} | {:throw, term(), Frame.t(), State.t()}`.
**Data Shape:** operands are decoded lists; values live at frame stack head; successful actions rebuild only the frame stack, while nullish object conversion and invalid `instanceof` return typed throw tuples.

### Decisive source
```elixir
def execute(name, [], %{stack: [right, left | stack]} = frame, execution)
    when name in @binary_operations,
    do: next(%{frame | stack: [Value.binary(name, left, right) | stack]}, execution)
def execute(:to_object, [], %{stack: [value | _]} = frame, execution)
    when value in [nil, :undefined],
    do: {:throw, {:type_error, :cannot_convert_to_object}, frame, execution}
def execute(:instanceof, [], %{stack: [constructor, object | stack]} = frame, execution) do
  with "function" <- Invocation.typeof(constructor, execution),
       {:ok, %Reference{} = prototype} <- Invocation.instanceof_prototype(constructor, execution) do
    next(%{frame | stack: [is_struct(object, Reference) and Property.prototype_chain_contains?(object, prototype, execution) | stack]}, execution)
  else _ -> {:throw, {:type_error, :invalid_instanceof_target}, frame, execution} end
end
```

**Flow:** family membership selects this adapter; it delegates arithmetic/coercion/callability to canonical layers; it leaves State ownership intact; exceptional preconditions become interpreter-consumable `:throw` actions.
**Invariant:** adapters never duplicate value semantics or run JS recursively; operand order is restored (`left` then `right`) before delegation, and typed errors remain catchable VM reasons.
**Probe:** `test/vm/runtime/opcode_test.exs` value-opcode test and callable/prototype test (:43-60, :192-215).

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "quickbeam", query: "Opcode.Value execute Value.binary instanceof cannot_convert_to_object", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the closed family-adapter pattern and canonical delegation. Adapt value representations and prototype storage. Omit direct semantic duplication. Coverage caveat: MCP unavailable; source and direct ExUnit tests were read.
