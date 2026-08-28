<!-- capsule-v2 -->
# export-boundary-value-conversion — How do you convert an owner-local JS value graph into safe plain BEAM terms at the public boundary, and what must be rejected?

**Source:** QuickBEAM MIT `master@c21c0e315213d0801950aae48cccedb3051c32d8`; Codebase Memory `quickbeam`. **Question:** Which JS values may cross the evaluation boundary as plain terms, and how do you stop live references, functions, symbols, and cycles from leaking out of an isolated heap?

## Export conversion with seen-map cycle guard seam
**Path/Symbol:** `lib/quickbeam/vm/runtime/value/export.ex` (107L whole): `value/2` (:19-21, entry), `convert/3` 8 clauses (:23-65), `convert_object/3` (:67-95), `convert_list/4` (:97-106); wired at `lib/quickbeam/vm/runtime/interpreter.ex:199` (`finish({:ok, value, execution})` → `Export.value`); consumed by heap_test cycle probe.
**Signature:** `value(term(), State.t()) :: {:ok, term()} | {:error, term()}`; internal `convert(term(), State.t(), seen) :: {:ok, term()} | {:error, term()}` with `seen :: %{non_neg_integer() => true}`.
**Data Shape:** rejection vocabulary: `{:error, :function_result}` (closures, program functions, callable objects), `{:error, :symbol_result}`, `{:error, :pending_promise_result}`, `{:error, {:cyclic_result, id}}`, `{:error, {:invalid_reference, id}}`, `{:error, %QuickBEAM.JSError{}}` (rejected promise reason converted via `Exception.to_js_error`).

### Decisive source
```elixir
defp convert(%PromiseReference{} = promise, execution, seen) do
  case Promise.state(execution, promise) do
    {:fulfilled, value} -> convert(value, execution, seen)
    {:rejected, reason} -> {:error, Exception.to_js_error(reason, execution, [])}
    :pending -> {:error, :pending_promise_result}
  end
end

defp convert(%Reference{id: id} = reference, execution, seen) do
  if Map.has_key?(seen, id) do
    {:error, {:cyclic_result, id}}
  else
    case Heap.fetch_object(execution, reference) do
      {:ok, object} -> convert_object(object, execution, Map.put(seen, id, true))
      :error -> {:error, {:invalid_reference, id}}
    end
  end
end

defp convert({:closure, _function, _references}, _execution, _seen),
  do: {:error, :function_result}
```

**Flow:** the interpreter's finish path hands the raw result value to `Export.value` → promises unwrap one level (fulfilled value recurses; rejected reason becomes a public JSError; a still-pending promise is a typed error, never a block) → heap references convert their object: callable objects and functions/symbols are REJECTED outright (no live behavior escapes), arrays map holes to `:undefined` and recurse, plain objects keep only enumerable non-Symbol data properties (accessors are skipped via `property_descriptor` value extraction) and recurse → every object id enters the `seen` map before recursion, so a self-referencing object fails with `{:cyclic_result, id}` instead of looping → primitives pass through unchanged; lists recurse element-wise with fail-fast on the first error.
**Invariant:** (1) nothing that carries behavior or identity (functions, symbols, live references) ever crosses the boundary — rejection is a typed error, not a lossy coercion; (2) conversion is total and terminating — the seen-map guarantees cycles fail instead of diverging; (3) the conversion happens INSIDE the owner process while the heap is still alive (`finish/1` runs before the worker exits), so no converted term can dangle; (4) a rejected promise's reason is converted through the same JSError dialect as a thrown error, so callers see one error shape.
**Probe:** `test/vm/runtime/heap_test.exs` :123-127 ("rejects cyclic owner-local objects during result conversion" — object with `self` property → `{:error, {:cyclic_result, object.id}}`); `test/vm/runtime/error_test.exs` (JSError dialect for rejected reasons); end-to-end results in `test/vm/measurement_test.exs` :10 (`{:ok, %{"answer" => 42}}` — plain maps out).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "quickbeam", query: "Export.value convert cyclic_result function_result pending_promise_result convert_object Interpreter.finish", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt allow-by-shape, reject-by-typed-error export conversion: primitives and plain data pass, behavior-carrying values (functions, symbols) and unresolvable states (pending promises, cycles) fail with a closed error vocabulary — this is the contract that makes "results are plain terms" true. Adopt the seen-map-before-recursion pattern for any graph conversion. Adapt the rejection set to your value model (e.g. allow boxed primitives if your heap has them); adapt the JSError conversion to your error dialect. Omit the array-hole → `:undefined` mapping only if your host preserves holes differently. Caveat: direct-read fallback (Codebase Memory MCP not connected this session); Retrieve block is a documented live-call template, not an executed call.
