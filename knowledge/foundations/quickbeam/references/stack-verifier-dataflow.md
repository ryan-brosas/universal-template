<!-- capsule-v2 -->
# stack-verifier-dataflow — How do you prove a decoded instruction stream is stack-safe before anything executes it?

**Source:** QuickBEAM MIT `master@c21c0e31`; Codebase Memory `quickbeam`. **Question:** What exact dataflow property does the bytecode verifier establish, and who reuses its result?

## Worklist stack-dataflow seam
**Path/Symbol:** `lib/quickbeam/vm/bytecode/verifier/stack.ex` — `verify/1` (:32-40), `analyze/1` (:50-59), `walk/1` (:63-81), `variable_pops/2` (:83-86), transition clauses (:88-120, :146-157, :181, :196).
**Signature:** `verify(Function.t()) :: :ok | {:error, term()}`; `analyze(Function.t()) :: {:ok, %{levels: %{pc => {depth, catch_index}}, maximum: non_neg_integer()}} | {:error, term()}`.
**Data Shape:** levels map: every REACHABLE instruction index → one consistent `{stack_depth, active_catch_target}`; `maximum` tracks the deepest observed depth.

### Decisive source
```elixir
{depth, catch_index} = Map.fetch!(state.levels, index)
{opcode, operands} = elem(state.function.instructions, index)
{name, _size, pops, pushes, format} = Opcode.info(opcode)
pops = pops + variable_pops(format, operands)

if depth < pops do
  {:error, {:stack_underflow, index, depth, pops}}
else
  next_depth = depth + pushes - pops
  ...
```

**Flow:** seed pc 0 with `{0, nil}` → worklist walk: each reachable instruction must find an ALREADY-AGREED (depth, catch) level or the analysis errors; npop/npop_u16/npopx formats add their encoded pop count on top of the static pop count; goto joins target at same depth/catch; conditionals join both arms; gosub/with_* push extra depths on their exceptional edges; catch sets itself as the new active catch target for its handler region; terminal ops stop propagation. `verify/1` then demands `analysis.maximum == function.stack_size` (declared max) — underflow, disagreement, and mismatch are all typed errors like `{:stack_underflow, index, depth, pops}`.
**Invariant:** (1) One instruction, one stack state: any join that would observe two different depths is rejected, so downstream consumers never branch on "maybe" stack shapes. (2) The declared `stack_size` is not trusted — it is DERIVED-and-compared; a lying header fails with `{:stack_size_mismatch, declared}`. (3) Exceptional control flow is part of the type state: catch targets ride along as the second component so handlers are verified with their real entry depth. (4) The result is computed ONCE and consumed twice — `Verifier.verify/1` gates program loading, and the compiler tier's `Pure.analyze_plan/2` reuses the very same `levels` to prove every generated block starts at a known depth.
**Probe:** `grep -c 'stack_underflow' lib/quickbeam/vm/bytecode/verifier/stack.ex` → 4 raise sites observed (:70, :116, :196 + doc/type context).
**Probe:** `grep -n 'levels: %{0 => {0, nil}}' lib/quickbeam/vm/bytecode/verifier/stack.ex` → line 52 (observed).
**Probe (indirect tests):** pure_test.exs CFG/malformed-target tests (:22-56) exercise Stack.analyze via analyze_plan's agreement gate; no dedicated verifier_test.exs exists in the graph's test inventory — coverage flows through decode + compiler suites (recorded caveat).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "quickbeam", query: "stack depth dataflow verifier catch target worklist join", limit: 5 });
```
(observed rank-1..2: stack.catch_level :146, stack.maybe_leave_catch :150-157; rank-4: verifier.verify_stack verifier.ex:335-340)

## Verdict
Adopt single-consistent-state worklist dataflow verification before executing any decoded IR, and design the analysis output (`levels`, `maximum`) as a reusable artifact for later tiers rather than a boolean gate. Adapt the opcode metadata table (pops/pushes/format) and exception-edge encoding to your ISA. Omit catch tracking only if your IR has no exception edges. Coverage: cited path no_recorded_issue+metadata_match @ gen 2026-08-25T19:58:40Z.
