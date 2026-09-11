<!-- capsule-v2 -->
# Exact block charging — how does generated code consume interpreter step fuel without ever over- or under-charging across a block boundary?

**Source:** QuickBEAM MIT `master@c21c0e315213d0801950aae48cccedb3051c32d8`; Codebase Memory `quickbeam`. **Question:** How do you let a JIT'd block execute many instructions per call while keeping hard step/memory limits exact and deopt points effect-free?

## Connected graph-selected seam
**Path/Symbol:** `lib/quickbeam/vm/compiler/runtime.ex:charge_block/4` (lines 176-197), `execute_plan/4` (lines 114-138).
**Signature:** `charge_block(Lease.t(), Frame.t(), State.t(), pos_integer()) :: {:ok, Frame.t(), State.t()} | action()`; `execute_plan(Lease.t(), Frame.t(), State.t(), plan()) :: action()`.
**Data Shape:** plan = `%{optional(pc) => {[operation()], block_boundary()}}` where operation = `{family, name, operands}` with family ∈ stack|local|value|branch; action = `{:ok,Frame,State} | {:deopt,Deopt.t()} | {:invoke,…} | {:error,term(),State.t()} | {:error,term()}`; `@max_block_instruction_count 256` re-checked at runtime.

### Decisive source
```elixir
def charge_block(%Lease{owner: owner}, _frame, _execution, _count) when owner != self(),
  do: {:error, :compiler_lease_owner_mismatch}

def charge_block(_lease, _frame, %State{memory_exceeded: true} = execution, _count),
  do: {:error, {:limit_exceeded, :memory_bytes, execution.memory_limit}, execution}

def charge_block(%Lease{}, %Frame{} = frame, %State{remaining_steps: remaining} = execution, count)
    when is_integer(count) and count > 0 and remaining >= count do
  {:ok, frame, %{execution | remaining_steps: remaining - count}}
end

def charge_block(%Lease{} = lease, %Frame{} = frame, %State{} = execution, count)
    when is_integer(count) and count > 0,
    do: deopt(:step_boundary, lease, frame, execution)

{:ok, invalid} -> {:error, {:invalid_compiler_block_plan, frame.pc, invalid}}
:error -> deopt(:unsupported_semantics, lease, frame, execution)
```

**Flow:** every ABI entry checks lease ownership FIRST (`owner != self()` → `{:error, :compiler_lease_owner_mismatch}`), then logical memory failure BEFORE any charging (the error carries the UNCHANGED execution state), then the single guard `remaining >= count` decides all-or-nothing: charge exactly `count`, or deopt `:step_boundary` with a before-instruction Deopt built from the uncharged state. `execute_plan` dispatches on `frame.pc`; empty blocks deopt immediately; missing pc keys mean "this instruction was never lowered" → `:unsupported_semantics`; oversized plans are rejected at runtime too (`{:invalid_compiler_block_plan, pc, invalid}`), never trusting the emitter-side cap.
**Invariant:** there is NO partial block charge — a block either executes whole or not at all; deopt always reconstructs state at an instruction that has consumed zero steps and performed zero effects (matches the pass-1 validated-deopt contract). Step fuel stays meaningful across tiers because pass-1's `add_generated_steps/2` restores unburned remainder on exit.
**Probe:** `test/vm/compiler/runtime_test.exs:12-25`: `execution(5)` + `charge_block(…,3)` → exactly 2 remain; second `charge_block(…,3)` → `{:deopt, %Deopt{reason: :step_boundary, frame == original frame, execution.remaining_steps == 2, phase: :before_instruction}}`. Lines 27-44 pin cross-process owner mismatch for both `charge_block` and `deopt`; lines 46-52 pin memory-before-charging. Probe executed: grep runtime.ex → `step_boundary` ×2 (169,194), `compiler_lease_owner_mismatch` ×3 (150,177,202), `invalid_compiler_block_plan` ×1 (130), `@max_block_instruction_count 256` ×3 uses (72,122,238).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "quickbeam", query: "charge block remaining steps deopt step boundary", limit: 5 });
// observed: runtime.charge_block #1 (runtime.ex:196-197), deopt.validate_boundary #2,
// compiler.add_generated_steps #3, counter.add_generated_steps #4, runtime.charge_state #5.
```

## Verdict
Adopt owner-check → memory-check → all-or-nothing step charging with deopt-before-partial-block; adapt the fuel unit (here "steps") and the memory flag source to your interpreter's limit model; omit per-operation charging inside guaranteed blocks (it defeats the JIT's purpose) but keep the runtime-side block-size cap as defense against a buggy planner. Coverage: both cited paths returned `no_recorded_issue` + `metadata_match`.
