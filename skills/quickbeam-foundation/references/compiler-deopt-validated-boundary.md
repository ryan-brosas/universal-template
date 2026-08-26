<!-- capsule-v2 -->
# compiler-deopt-validated-boundary — How does optimized code yield mid-frame to the interpreter without duplicating effects or trusting its own state?

**Source:** QuickBEAM MIT `master@c21c0e31`; Codebase Memory `quickbeam`. **Question:** What must a deopt record contain so the interpreter can resume blind — and how is that enforced?

## Validated before-instruction deopt seam
**Path/Symbol:** `lib/quickbeam/vm/compiler/deopt.ex:new/6` (:60-87), `validate/1` (:91-102), validators (:106-144).
**Signature:** `new(reason, artifact_key, pool_epoch, generation, Frame.t(), State.t()) :: {:ok, t()} | {:error, term()}`; reason ∈ `:unsupported_opcode | :unsupported_semantics | :step_boundary | :suspension_boundary | {:guard_failed, atom()}`.
**Data Shape:** `%Deopt{artifact_key: 32-byte binary, pool_epoch: ≥0, generation: ≥0, reason, owner: pid(), frame: Frame.t(), execution: State.t(), contract_version, phase: :before_instruction}`.

### Decisive source
```elixir
defp validate_owner(owner) when owner == self(), do: :ok
defp validate_owner(owner), do: {:error, {:deopt_owner_mismatch, owner, self()}}

defp validate_phase(:before_instruction), do: :ok

defp validate_boundary(%Frame{pc: pc, function: %{instructions: instructions}})
     when is_integer(pc) and pc >= 0 and is_tuple(instructions) and
            pc < tuple_size(instructions),
     do: :ok
```

**Flow:** generated code hits an unsupported opcode / suspension point (await, call) / guard failure → builds a Deopt at the CURRENT pc (next unexecuted instruction) → validate pins owner==self(), contract version, key byte width, counters ≥0, closed reason set, pc inside the instruction tuple → orchestrator's `resume_action({:deopt, deopt}, _)` calls `Interpreter.resume_deopt_raw/1`, which re-dispatches the exact instruction in the interpreter.
**Invariant:** (1) Deopt state is owner-local: only the process that built it may resume it — leases/artifacts from other epochs cannot smuggle frames across processes. (2) The boundary is strictly BEFORE an instruction: nothing executed, no step consumed, no observable effect — so interpreter resumption can neither duplicate nor skip effects. (3) Every field of the handoff is validated at construction; the interpreter trusts the struct because validation, not convention, guarantees it. (4) Stale artifacts fail with `{:stale_compiler_contract, version}` instead of misinterpreting foreign bytecode.
**Probe:** `grep -c ':before_instruction' lib/quickbeam/vm/compiler/deopt.ex` → 3 (observed: struct default, type, validator).
**Probe (test):** test/vm/compiler/contract_test.exs "deoptimization state is owner-local and points before a valid instruction" (:102+) constructs one via `Deopt.new(:unsupported_opcode, artifact_key, 1, 2, frame, execution)`.

## Get live surrounding code
**Retrieve:**
await mcp.codebase_memory.search_graph({ project: "quickbeam", query: "deoptimization validated owner-local boundary interpreter transition", limit: 5 });
```
(observed rank-2: compiler.deopt.validate_owner deopt.ex:119)

## Verdict
Adopt "validate-at-construction, trust-at-resume" deopt records for any tiered executor (JIT → interpreter, wasm fast path → slow path, native callback → VM loop). Adapt the reason set and epoch/generation fields to your versioning story. Omit the pool_epoch fields if your tier has no restartable module cache. Coverage: cited path no_recorded_issue+metadata_match @ gen 2026-08-25T19:58:40Z.
