<!-- capsule-v2 -->
# opcode-control-explicit-action-algebra — How should control opcodes encode flow, completion, throws, and await variants?

**Source:** QuickBEAM MIT `master@c21c0e315213d0801950aae48cccedb3051c32d8`; Codebase Memory `quickbeam` (not connected in-session — direct source/test fallback). **Question:** How does a control adapter keep branching and suspension data explicit while leaving scheduling to the interpreter?

## Control action boundary
**Path/Symbol:** `lib/quickbeam/vm/runtime/opcode/control.ex:1-91`, `execute/4`; consumer `runtime/interpreter.ex` opcode reducer.
**Signature:** `execute(atom(), [term()], Frame.t(), State.t()) :: action()` where action is a closed union of `:next`, `:run`, `:return`, `:return_async`, `:throw`, and three await forms.
**Data Shape:** branch actions carry a new pc; return actions carry a value; await actions carry either PromiseReference, legacy reference, or immediate `{:ok|:error, value}` plus the frame with consumed operand.

### Decisive source
```elixir
def execute(:catch, [target], frame, execution), do: next(%{frame | stack: [{:catch, target} | frame.stack]}, execution)
def execute(name, [target], %{stack: [value | stack]} = frame, execution)
    when name in [:if_true, :if_true8],
    do: {:run, %{frame | pc: if(Value.truthy?(value), do: target, else: frame.pc + 1), stack: stack}, execution)
def execute(:throw, [], %{stack: [value | stack]} = frame, execution),
  do: {:throw, value, %{frame | stack: stack}, execution)
def execute(:await, [], %{stack: [%PromiseReference{} = promise | stack]} = frame, execution),
  do: {:await_promise, promise, %{frame | stack: stack}, execution)
def execute(:await, [], %{stack: [value | stack]} = frame, execution),
  do: {:await_immediate, {:ok, value}, %{frame | stack: stack}, execution)
```

**Flow:** decode selects the control family; adapter consumes stack operands; `:run` delegates pc stepping, completion delegates return/finalization, throws delegate exception unwinding, and await tags delegate async/legacy machinery.
**Invariant:** control opcodes choose actions but never perform stepping, promise scheduling, or unwinding themselves; await representation is not conflated, preventing legacy refs from entering Promise machinery.
**Probe:** `test/vm/runtime/opcode_test.exs` control test (:63-84); `interpreter_test.exs` nested await and throw/catch tests (:236-300).

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "quickbeam", query: "Opcode.Control await_immediate await_promise return_async", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt explicit action algebra and thin control adapters. Adapt scheduler action names. Omit embedding interpreter loops in opcode handlers. Coverage caveat: MCP unavailable; direct source/test reads are authoritative.
