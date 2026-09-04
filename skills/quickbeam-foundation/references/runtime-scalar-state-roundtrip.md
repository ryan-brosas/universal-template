<!-- capsule-v2 -->
# Scalar compact-state round-trip — how does generated code suspend into a compact tuple and resume as a canonical interpreter frame?

**Source:** QuickBEAM MIT `master@c21c0e315213d0801950aae48cccedb3051c32d8`; Codebase Memory `quickbeam`. **Question:** When a JIT'd scalar block must hand control back (deopt or call), how is frame state carried compactly and rebuilt without losing re-entry safety?

## Connected graph-selected seam
**Path/Symbol:** `lib/quickbeam/vm/compiler/runtime.ex:deopt_state/4` (lines 212-233), `charge_state/4` (lines 149-172), `invoke_state/5` (lines 605-628).
**Signature:** `deopt_state(Deopt.reason(), Lease.t(), {Frame.t(), pc, args, locals, stack}, State.t()) :: action()`; `invoke_state(callable, args, this, state_tuple, State.t()) :: action()`.
**Data Shape:** scalar generated code carries `{%Frame{}, pc, args::tuple(), locals::tuple(), stack::list()}` instead of rebuilding `%Frame{}` per operation; guards pin every component (`is_integer(pc) and pc >= 0`, tuples for args/locals, list for stack).

### Decisive source
```elixir
def deopt_state(reason, %Lease{} = lease,
      {%Frame{} = frame, pc, args, locals, stack}, %State{} = execution)
    when is_integer(pc) and pc >= 0 and is_tuple(args) and is_tuple(locals) and is_list(stack) do
  frame = %{
    frame
    | pc: pc, args: args, locals: locals, stack: stack,
      compiler_allow_reentry: scalar_profile?(execution)
  }
  deopt(reason, lease, frame, execution)
end

defp scalar_profile?(%State{compiler_context: %{profile: :scalar_v1}}), do: true
defp scalar_profile?(_execution), do: false
...
caller = %{
  frame
  | pc: pc, args: args, locals: locals, stack: stack,
    compiler_allow_reentry: true, compiler_entered: false
}
{:invoke, callable, arguments, this, caller, execution, false}
```

**Flow:** malformed state tuples never raise inside generated code — they become typed errors (`{:invalid_compiler_scalar_state, state}`, `{:invalid_compiler_invocation_state, state}`, `{:invalid_compiler_scalar_charge, count, state}` from `charge_state`'s catch-all). Deopt rebuilds the canonical frame with `compiler_allow_reentry` derived from the execution profile (only `:scalar_v1` grants it); invocation builds an explicit interpreter-owned caller with `compiler_allow_reentry: true` AND `compiler_entered: false`, returning a 7-tuple invoke action the interpreter resumes.
**Invariant:** the compact representation is only ever an optimization of the canonical frame — every exit path (deopt, invoke, error) reconstructs a full `%Frame{}` before crossing back to interpreter code, so the interpreter never sees compiler-private shapes; re-entry flags are set by profile policy at the boundary, not by the generated code itself.
**Probe:** probe executed: grep runtime.ex → `compiler_allow_reentry` ×2 (line 226 profile-derived, line 620 unconditional-invoke), `compiler_entered` ×1 (line 621), `scalar_profile?` definition lines 630-631 matching exactly `profile: :scalar_v1`. Direct-test coverage note: runtime_test.exs covers the frame-based charging/deopt paths directly (its lease/frame fixtures) but does NOT exercise deopt_state/invoke_state — those are covered indirectly by the scalar-profile suites (pass-1 pure/scalar evidence); recorded as a coverage caveat.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "quickbeam", query: "deopt state rebuild frame scalar invoke caller", limit: 5 });
// observed: profile.scalar.deopt_call #1-#2 (scalar.ex), Runtime.deopt_state #3 (runtime.ex:232-233),
// wasm.import_rewriter.rebuild #4 noise, compiler.invoke_frame #5. The seam ranks in the top cluster
// but scalar-profile functions co-rank — disambiguate on file path runtime.ex.
```

## Verdict
Adopt the guard-pinned compact-state tuple with typed malformed-shape errors and canonical-frame reconstruction at every tier boundary; adapt the `compiler_allow_reentry` policy source (here the `:scalar_v1` profile flag in execution context) to your own tier metadata; omit direct reuse of the 7-tuple invoke action shape unless your interpreter consumes the same envelope. Coverage caveat: `deopt_state`/`invoke_state` lack a dedicated direct test range; rely on runtime_test's adjacent fixtures plus scalar-suite integration evidence. Both cited paths returned `no_recorded_issue` + `metadata_match`.
