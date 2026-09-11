<!-- capsule-v2 -->
# scalar-eligibility-ladder — Which functions may be lowered to scalar block forms, and how is "safe to keep locals in tuples" proven?

**Source:** QuickBEAM MIT `master@c21c0e315213d0801950aae48cccedb3051c32d8`; Codebase Memory `quickbeam`. **Question:** What gates decide whether a verified function gets the faster scalar lowering (locals/args as BEAM tuples) instead of the generic pure profile, and which gate catches a local read that may observe an uninitialized slot?

## Nine-gate eligibility ladder seam
**Path/Symbol:** `lib/quickbeam/vm/compiler/profile/scalar.ex:eligibility/3` (:78-97), `within_limit/3` (:99-100), `require_eligibility/2` (:102-103), `bounded_blocks?/1` (:105-106), `bounded_levels?/1` (:108-109), `captured_frame_slots?/1` (:202-209), `checked_locals_initialized?/2` (:111-199); limit attrs :15-19. Caller: `profile/pure.ex:scalar_eligibility/2` (:78-88) runs `analyze_plan` first, so eligibility only ever sees a stack-verified plan.
**Signature:** `eligibility(%Function{}, plan(), levels()) :: :eligible | {:ineligible, atom()}`; `lower/3` returns `{:ok, %Template{}} | :not_eligible`.
**Data Shape:** nine sequential gates, first failure wins: `stack_size <= 64`, `arg_count <= 8`, `var_count <= 8`, `map_size(plan) <= 16` blocks, total lowered ops `<= 64`, every block `<= 32` ops, every analyzed level depth `<= 64`, no captured frame slots, checked-locals initialized on all paths.

### Decisive source
```elixir
@max_stack_depth 64
@max_argument_count 8
@max_variable_count 8
@max_scalar_operations 64
@max_scalar_blocks 16

defp bounded_blocks?(plan),
    do: Enum.all?(plan, fn {_pc, {operations, _reason}} -> length(operations) <= 32 end)

defp bounded_levels?(levels),
    do: Enum.all?(levels, fn {_pc, {depth, _catch}} -> depth <= @max_stack_depth end)

defp apply_initialization([{:local, :get_loc_check, [index]} | operations], initialized) do
    if MapSet.member?(initialized, index),
      do: apply_initialization(operations, initialized),
      else: :unsafe
  end

defp merge_initialization_successor(successor, initialized, {entries, queue}) do
    case Map.fetch(entries, successor) do
      :error ->
        {Map.put(entries, successor, initialized), [successor | queue]}

      {:ok, existing} ->
        merged = MapSet.intersection(existing, initialized)

        if merged == existing,
          do: {entries, queue},
          else: {Map.put(entries, successor, merged), [successor | queue]}
    end
  end
```

**Flow:** `Pure.scalar_eligibility/2` → `analyze_plan` (stack dataflow + CFG + plan-size caps, pass-1 capsule) → `Scalar.eligibility/3` walks the nine gates in a `with` chain → any gate fails → `{:ineligible, reason}` → `Pure.template/4` falls back to the GENERIC template (`pure.ex:322-330`: `:not_eligible -> generic_template(generic_plan(plan))`). The checked-local gate is a worklist dataflow from pc 0 carrying a MapSet of initialized local indices per join point: `get_loc_check` requires membership (`:unsafe` otherwise), `set_loc_uninitialized` REMOVES the index, `put_loc`/`set_loc`/`put_loc_check(_init)` ADD it, and joins take MapSet INTERSECTION with re-enqueue only when the set actually shrank. Successors come from conditional branches (target AND fallthrough), gotos (target only), and `:continue` blocks (fallthrough).
**Invariant:** (1) Scalar is an optimization, never a requirement — every rejection path lands in the generic pure template, so a wrong "eligible" answer costs performance, not correctness, but a wrong "ineligible" answer must never happen: the gates are deliberately conservative (≤8 args/vars, ≤16 blocks, ≤64 ops). (2) A local read via `get_loc_check` is admitted only if EVERY path reaching it initialized the local — intersection-at-join means "initialized on all paths", not "on some path". (3) Captured frame slots (`closure_type` 0|1 in any constant function's closure_vars) disqualify the whole function because captured frame slots need cells, which scalar tuples cannot provide. (4) The rejection reason atom is diagnostic-only; callers branch on the `:eligible`/`{:ineligible, _}` shape, never on the reason.
**Probe:** `grep -n '@max_stack_depth\|@max_argument_count\|@max_variable_count\|@max_scalar_operations\|@max_scalar_blocks' lib/quickbeam/vm/compiler/profile/scalar.ex` → 5 hits at :15-19 (plus tuple-builder uses at :21/:24/:28/:38).
**Probe:** `grep -n 'closure_type' lib/quickbeam/vm/compiler/profile/scalar.ex` → exactly 1 hit (:205, inside `captured_frame_slots?`).
**Probe:** `test/vm/compiler/profile/pure_test.exs:73-87` — "reports bounded scalar eligibility rejections": a 9-argument function yields `{:ineligible, :argument_count}` (the first failing gate, since args are checked before vars/blocks); a `while` loop function yields `:eligible`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "quickbeam", query: "Scalar eligibility within_limit checked_locals_initialized captured_frame_slots", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the ordered conservative-gate ladder (cheap numeric bounds first, dataflow gates last) with first-rejection reporting for any tiered lowering where the fast tier has stricter shape requirements than the slow tier; adopt the intersection-at-join initialization worklist verbatim — it is the minimal correct "initialized on all paths" proof over a basic-block plan; adapt the five constants to your register/argument model; omit QuickBEAM's closure_type frame-capture check unless your fast tier also forbids cell capture. Evidence note: mined this pass via direct whole-file source + test read fallback (Codebase Memory MCP not connected in session); probes executed byte-for-byte, Retrieve not executed.
