<!-- capsule-v2 -->
# scalar-block-charge-preflight — How does generated scalar code consume the step budget without ever charging a partial block?

**Source:** QuickBEAM MIT `master@c21c0e315213d0801950aae48cccedb3051c32d8`; Codebase Memory `quickbeam`. **Question:** Where do step charges live in scalar-generated code — per block, per operation, or both — and how does a side-effecting read that can deopt still guarantee a consumed step?

## Per-block charge + single-op preflight seam
**Path/Symbol:** `lib/quickbeam/vm/compiler/profile/scalar.ex:block_clause/4` — empty-block clause (:259-266), single-op object/global-get_var clause (:268-286), general clause (:288-359); `charge_preflight/2` (:498-530); `state_bindings/7` (:532-538); `lower_property/3` (:474-496); `lower_global/5` get_var clause (:399-424). Segment splitting that makes this work: `profile/pure.ex:split_scalar_segments/3` (:230-247) + `preflight_instruction?/1` (:249-250) + `invocation_instruction?/1` (:252).
**Signature:** generated `block(pc, lease, {frame, args, locals, stack, execution})` clauses; `Runtime.charge_state(lease, compact_tuple, execution, count) :: {:ok, compact_tuple} | action`.
**Data Shape:** three clause shapes per plan: empty block → immediate `deopt_from_arguments(reason, pc, stack)`; a block of EXACTLY ONE object op or global `get_var` → uncharged direct lowering (the op carries its own preflight charge); any other block → one `charge_state(…, length(operations))` up front, then `case` on the result.

### Decisive source
```elixir
defp block_clause(pc, {[{family, name, _operands}] = operations, reason}, levels, tuple_mode)
     when family == :object or (family == :global and name == :get_var) do
    # ... no block-level charge; the single op lowers directly ...
    clause(block_arguments(pc, depth), [lower_operations(operations, reason, state)])
  end

defp block_clause(pc, {operations, reason}, levels, tuple_mode) do
    # ...
    lowered = lower_operations(operations, reason, state)

    compact = tuple([frame, integer(pc), args, locals, stack_expression(depth)])

    charge =
      remote_call(Runtime, :charge_state, [lease, compact, execution, integer(length(operations))])

    charged_body =
      case_expression(charge_result, [
        clause([tuple([atom(:ok), charged_state])], [lowered]),
        clause([action], [action])
      ])

    body = anonymous_call([clause([charge_result], [charged_body])], [charge])

    clause(block_arguments(pc, depth), [body])
  end

defp charge_preflight(state, continuation) do
    # ...
    charge =
      remote_call(Runtime, :charge_state, [state.lease, compact, state.execution, integer(1)])

    case_expression(charge, [
      clause([tuple([atom(:ok), continuation_state])], [continuation.(charged_state)]),
      clause([action], [action])
    ])
  end
```

**Flow:** plan segments are cut so every side-effecting read (`get_var`, `get_field`, `get_field2`, `get_array_el`, `get_length`) STARTS a fresh segment and every invocation ends one (`pure.ex:230-252`) → a 1-op read segment hits the uncharged single-op clause, where `lower_global`/`lower_property` emit `case Runtime.global_get/property_get of {ok, v} -> (charge_preflight: `case charge_state(…, 1)` → continue | action passthrough) | :deopt -> deopt_call(:unsupported_semantics, pc)` → a multi-op segment hits the general clause: ONE `charge_state` for the whole block, `{ok, charged_state}` unpacked via `state_bindings` (`erlang:element/2` matches 1..6 over the returned compact tuple — no `%Frame{}` rebuild mid-block), then the lowered body; ANY other result (a deopt/invoke action) is returned verbatim as the clause result, which the tier's 4-action contract (`compiler-tier-action-algebra`) funnels back to the interpreter.
**Invariant:** (1) No partial block charge: the block either runs fully after one all-or-nothing charge or exits with the action untouched — mirroring the runtime-side rule in `runtime-block-charge-exact-deopt`. (2) A side-effecting read consumes AT LEAST one step even when it deopts: the preflight charge sits between the successful read and the continuation, so the read's effect and its step cost commit together. (3) Charging may conservatively EXCEED the operation count (a multi-op block containing a `get_var` pays block charge + preflight charge) but never fall below it — overcharging only deopts earlier, and the validated deopt boundary makes that safe. (4) The compact tuple is the ONLY state shape crossing the charge call; canonical frames exist only at deopt/invoke boundaries.
**Probe:** `grep -n 'charge_state' lib/quickbeam/vm/compiler/profile/scalar.ex` → exactly 2 hits: :334 (block charge, `length(operations)`) and :524 (preflight charge, literal `1`).
**Probe:** `grep -n 'defp preflight_instruction?\|defp invocation_instruction?' lib/quickbeam/vm/compiler/profile/pure.ex` → 2 hits (:249/:252); `grep -rn ':not_eligible' lib/quickbeam/vm/compiler/profile/` → 3 hits (pure.ex:327 fallback site, scalar.ex:48/:53 specs, :72 return).
**Probe:** `test/vm/compiler/runtime_test.exs:12-52` (pass-2) pins the runtime half of the same contract: `charge_block` with remaining < count deopts `:step_boundary` with the uncharged state preserved — the generated code's single up-front charge is what makes "uncharged state preserved" meaningful.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "quickbeam", query: "Scalar block_clause charge_state charge_preflight state_bindings", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-tier charging pattern for any generated-code tier with a step budget: one all-or-nothing charge per basic block plus a mandatory 1-unit preflight charge around every side-effecting primitive that can bail mid-operation; adopt the action-passthrough `case` shape (continue on `{ok, state}`, return anything else verbatim) so the generator never has to know the action algebra; adapt the segment-cutting rules to your opcode set (cut before side-effecting reads, after invocations); omit QuickBEAM's element-wise state unpacking if your ABI can pass the compact state as a struct. Evidence note: mined this pass via direct whole-file source + test read fallback (Codebase Memory MCP not connected in session); probes executed byte-for-byte, Retrieve not executed.
