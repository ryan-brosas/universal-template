<!-- capsule-v2 -->
# pure-profile-bounded-plan — How do you lower bytecode to generated code when the input is attacker-controlled and every cost must be bounded?

**Source:** QuickBEAM MIT `master@c21c0e31`; Codebase Memory `quickbeam`. **Question:** Which functions get compiled, how large can a lowering plan get, and what does generated code actually contain?

## Bounded plan / candidacy seam
**Path/Symbol:** `lib/quickbeam/vm/compiler/profile/pure.ex` (563L) — `candidate?/3` (:50-54), `analyze_plan/2` (:114-125), bounds `@max_block_instruction_count 256`/`@max_block_count 4_096`/`@max_lowered_instruction_count 4_096`/`@max_region_operations 32` (:19-22), `plan_block/2` (:254-264), `boundary_reason/4` + `deopt_reason/1` (:291-306), `fast_block_clause/4` vs `stepped_block_clause/4` (:409-458), `validate_plan_size/1` (:308-322).
**Signature:** `candidate?(Function.t(), minimum, :pure_v1 | :scalar_v1) :: boolean()`; `prepare(Function.t(), minimum, profile) :: {:ok, Template.t(), count} | {:skip, count} | {:error, term()}`.
**Data Shape:** plan = `%{start_pc => {operations, boundary_reason}}`; operation = `{family, name, operands}` with family ∈ stack|local|value|branch (+ scalar object/invocation extensions).

### Decisive source
```elixir
def candidate?(%Function{instructions: instructions}, minimum, profile) ... do
  minimum <= 1 or tuple_size(instructions) >= minimum or backward_branch?(instructions)
end

defp validate_plan_size(plan) when map_size(plan) > @max_block_count,
  do: {:error, {:compiler_resource_limit, :blocks, map_size(plan), @max_block_count}}
```
```elixir
execute =
  remote_call(Runtime, :execute_fast_block, [
    lease, frame, execution,
    :erl_parse.abstract(operations)
  ])
```

**Flow:** frame entry → `candidate?` rejects tiny straight-line nested functions BEFORE artifact hashing (loops always pass via backward-branch detection over goto/if_false-family targets ≤ pc) → CFG blocks → per-block `Enum.split_while(supported?)` with a 256-instruction cap; the first unsupported instruction names the boundary reason (`:suspension_boundary` for await/call family, else `:unsupported_opcode`; over-cap becomes `:unsupported_semantics`) → whole-plan size validated against 4096-block / 4096-op limits as typed `{:compiler_resource_limit, ...}` errors → template emitted whose clauses NEVER inline semantics: fast blocks delegate wholesale to `Runtime.execute_fast_block` with abstract'd operands; slow blocks `charge_block` then step `{pc, index}`-keyed through `Runtime.execute_stack/local/value/branch`; every clause tail either continues to the next block or `Runtime.deopt(reason)`.
**Invariant:** (1) Compilation cost is bounded three ways (block length, block count, lowered-op count) and exceeding any bound is a typed error, not a larger artifact. (2) Loops are exempt from the size prefilter — hot small loops stay compilable while cold one-shot nested closures are rejected pre-hash. (3) Generated modules contain NO semantics — only control flow over canonical Runtime ABI calls — so a lowering bug degrades performance, never correctness. (4) Lowering requires verifier agreement: `analyze_plan/2` fails with `{:stack_size_mismatch, declared}` unless `Stack.analyze(function).maximum == function.stack_size`. (5) Region tier exists only for scalar_v1+regions, takes ≤32 ops from the entry block, and drops a terminal branch so it never falls off the end of a loop body.
**Probe:** `grep -c 'deopt_call(' lib/quickbeam/vm/compiler/profile/pure.ex` → 6 call sites + defp pair observed at lines 388-546.
**Probe:** bound attributes at pure.ex lines 19-22 (observed: 256 / 4_096 / 4_096 / 32).
**Probe (test):** pure_test.exs "extracts a bounded scalar entry region" (:90-107): a 100-statement function yields `{:skip, 3}` for full-frame but `{:ok, region_template, 32}` for prepare_region with ≤17 block clauses.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "quickbeam", query: "bounded compiler profile basic block plan eligibility scalar lowering", limit: 5 });
```
(observed rank-3..4: pure.plan_block pure.ex:254-264, pure.extended_scalar_plan? :156-160)

## Verdict
Adopt bounded-plan candidacy + delegation-only codegen for any JIT-style tier over untrusted input. Adapt the opcode whitelist tables (@core/@extended_scalar_operations) to your ISA. Omit the stepped/slow-path split if all your supported ops are cheap enough to charge per block. Coverage: cited path no_recorded_issue+metadata_match @ gen 2026-08-25T19:58:40Z.
