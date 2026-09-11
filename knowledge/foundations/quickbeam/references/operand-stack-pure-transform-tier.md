<!-- capsule-v2 -->
# operand-stack-pure-transform-tier — How do you share one operand-stack permutation implementation between an interpreter and generated compiler blocks without letting either advance the pc?

**Source:** QuickBEAM MIT `master@c21c0e315213d0801950aae48cccedb3051c32d8`; Codebase Memory `quickbeam` (not connected in-session — direct source+test read fallback). **Question:** Where does the stack-permutation semantics of stack-family opcodes live so the interpreter and the compiled tier cannot drift?

## Two-tier pure stack transform seam
**Path/Symbol:** `lib/quickbeam/vm/runtime/stack.ex` (79L whole, `execute/5` clause ladder :13-78); wrapper `lib/quickbeam/vm/runtime/opcode/stack.ex` (61L whole, `@opcodes` list :14-45, `execute/4` :55-61); compiler-tier consumer `lib/quickbeam/vm/compiler/runtime.ex` `execute_stack/4` (:258-263) + fast-block interior `OperandStack.execute` (:321).
**Signature:** `QuickBEAM.VM.Runtime.Stack.execute(name, operands, stack, this, constants) :: {:ok, [term()]} | {:error, term()}`; `Opcode.Stack.execute(name, operands, Frame.t(), State.t()) :: {:next, Frame.t(), State.t()}`.
**Data Shape:** pure list-in/list-out over bare Elixir lists (head = top of stack); `this` and `constants` are read-only inputs (`push_this` pushes `this`, `push_const`/`push_const8` index `constants`); `push_bigint_i32` wraps as `{:bigint, value}`. No State access at all in the inner tier.

### Decisive source
```elixir
# runtime/stack.ex — the ONLY implementation of stack permutation semantics
def execute(name, [value], stack, _this, _constants)
    when name in [:push_i32, :push_i8, :push_i16], do: {:ok, [value | stack]}
def execute(:push_bigint_i32, [value], stack, _this, _constants),
  do: {:ok, [{:bigint, value} | stack]}
def execute(:push_this, [], stack, this, _constants), do: {:ok, [this | stack]}
def execute(name, [index], stack, _this, constants) when name in [:push_const, :push_const8],
  do: {:ok, [Enum.at(constants, index) | stack]}
def execute(:dup2, [], [a, b | stack], _this, _constants), do: {:ok, [a, b, a, b | stack]}
def execute(:swap2, [], [a, b, c, d | stack], _this, _constants), do: {:ok, [c, d, a, b | stack]}
def execute(:rot5l, [], [a, b, c, d, e | stack], _this, _constants),
  do: {:ok, [e, a, b, c, d | stack]}
def execute(name, operands, stack, _this, _constants),
  do: {:error, {:invalid_stack_operation, name, operands, stack}}

# runtime/opcode/stack.ex — the interpreter wrapper owns frame/State plumbing
def execute(name, operands, %Frame{} = frame, %State{} = execution)
    when name in @opcodes and is_list(operands) do
  {:ok, stack} =
    OperandStack.execute(name, operands, frame.stack, frame.this, frame.function.constants)
  {:next, %{frame | stack: stack}, execution}
end

# compiler/runtime.ex — the generated-block tier calls the SAME inner function
def execute_stack(name, operands, %Frame{} = frame, %State{} = execution)
    when name in @stack_operations and is_list(operands),
    do: name |> Stack.execute(operands, frame, execution) |> advance_action()
```

**Flow:** interpreter dispatch → `Opcode.Stack.execute/4` (closed `@opcodes` gate) → inner `Runtime.Stack.execute/5` returns `{:ok, new_stack}` → wrapper rebuilds the frame, returns `{:next, frame, execution}` with pc UNCHANGED (stack ops never advance the pc; the interpreter loop owns stepping). Generated compiler blocks call the same inner function from `execute_stack/4` (which then advances the pc itself via `advance_action/1`) and from inside fast blocks (:321). Any unknown name or wrong operand/stack shape → `{:error, {:invalid_stack_operation, name, operands, stack}}` — a typed backstop behind the bytecode verifier, not a crash.
**Invariant:** the inner tier is total and pure — no State reads, no side effects, no pc knowledge — so both execution tiers share byte-identical permutation semantics by construction. The wrapper's `{:ok, stack}` match is intentionally unguarded: an `:error` from the inner tier is a verifier failure and should crash loudly, not degrade. The 30-opcode `@opcodes` list must stay disjoint from the other five opcode-family routing tables (pinned by opcode_test's first test).
**Probe:** `test/vm/runtime/opcode_test.exs` "stack opcodes transform explicit frames without advancing the program counter" (:25-40) — `Stack.execute(:dup2, ...)` → `{:next, %Frame{pc: 4, stack: [:a, :b, :a, :b, :c]}, ...}` (pc stays 4), plus `:swap`, `:push_const [1]` → `20` from constants, `:push_bigint_i32` → `{:bigint, 9}`; and "opcode families publish non-overlapping routing tables" (:17-23).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "quickbeam", query: "OperandStack execute stack permutation dup2 rot5l invalid_stack_operation", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-tier split: a pure total function over (name, operands, bare stack, read-only context) shared by every execution tier, plus thin per-tier wrappers that own frame/State plumbing and pc policy. Adapt the opcode set and the `{:bigint, _}` wrapper to your value model. Omit the interpreter/compiler duplication entirely — the whole point is one implementation. Caveat: the inner tier has no dedicated stack_test.exs; coverage is via opcode_test ranges and the compiler-tier suites (direct-read fallback, no graph coverage check in-session). `:nip_catch` shares the `:nip` arm — catch-marker removal is a stack permutation, not control flow.
