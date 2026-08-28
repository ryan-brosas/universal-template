<!-- capsule-v2 -->
# opcode-local-closure-global-cell-adapter — How should local and closure opcodes preserve mutable cell identity per evaluation?

**Source:** QuickBEAM MIT `master@c21c0e315213d0801950aae48cccedb3051c32d8`; Codebase Memory `quickbeam` (not connected in-session — direct source/test fallback). **Question:** How do compact locals, captured closures, and globals share explicit owner-local references?

## Local and closure adapter
**Path/Symbol:** `lib/quickbeam/vm/runtime/opcode/local.ex:1-315`, `execute/4`, `execute_compact/6`, `instantiate_function/4`, `read_global/2`, `write_global/3`.
**Signature:** `execute/4 :: action()`; `execute_compact/6 :: {:ok, tuple(), tuple(), [term()], State.t()}`.
**Data Shape:** frame args/locals are tuples; promoted slots become `{:cell, id}` and state `cells`; globals are state map entries with optional `globalThis` property mirroring; uninitialized checked reads throw `{:reference_error, index}`.

### Decisive source
```elixir
def execute(:get_loc_check, [index], frame, execution) do
  case read_slot(elem(frame.locals, index), execution) do
    :uninitialized -> {:throw, {:reference_error, index}, frame, execution}
    value -> push(frame, execution, value)
  end
end
defp promote_tuple_slot(tuple, index, execution) do
  case elem(tuple, index) do
    {:cell, _id} = reference -> {reference, tuple, execution}
    value ->
      id = execution.next_cell_id
      reference = {:cell, id}
      execution = Memory.charge_cell(execution, value)
      {reference, put_elem(tuple, index, reference), %{execution | cells: Map.put(execution.cells, id, value), next_cell_id: id + 1}}
  end
end
def read_global(execution, name) do
  case Map.get(execution.globals, "globalThis") do
    %QuickBEAM.VM.Runtime.Reference{} = global_this ->
      case Property.get(global_this, name, execution) do
        {:ok, :undefined} -> Map.fetch(execution.globals, name)
        {:ok, value} -> {:ok, value}
        {:error, _} -> Map.fetch(execution.globals, name)
      end
    _ -> Map.fetch(execution.globals, name)
  end
end
```

**Flow:** compact operation reads/writes tuple slots; captured values are promoted once and charged; later closures reuse the cell reference; global reads prefer globalThis but fall back to state globals; writes mirror both where possible.
**Invariant:** cell identity and heap ownership are evaluation-local, so concurrent evaluations cannot share mutations; checked uninitialized access is a typed JS reference error, not an accidental BEAM exception.
**Probe:** `test/vm/runtime/opcode_test.exs` local mutable-cell and closure promotion tests (:117-154); `interpreter_test.exs` captured-variable isolation tests (:30-58).

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "quickbeam", query: "Opcode.Local promote_tuple_slot read_global globalThis reference_error", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt owner-local cell promotion, compact tuple operations, and globalThis fallback. Adapt global storage and memory charging APIs. Omit shared mutable closure cells. Coverage caveat: MCP unavailable; direct source and ExUnit tests were read.
