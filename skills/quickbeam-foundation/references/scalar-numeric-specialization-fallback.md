<!-- capsule-v2 -->
# scalar-numeric-specialization-fallback — How does generated scalar code inline numeric ops without duplicating JS semantics?

**Source:** QuickBEAM MIT `master@c21c0e315213d0801950aae48cccedb3051c32d8`; Codebase Memory `quickbeam`. **Question:** When a lowered arithmetic/comparison op may see non-numeric values at runtime, how does the generator keep the fast path in BEAM while guaranteeing the slow path IS the canonical interpreter helper — and what makes region-mode tuple updates different from full-function mode?

## Guard-fallback specialization seam
**Path/Symbol:** `lib/quickbeam/vm/compiler/profile/scalar.ex:binary_expression/4` — compile-time constant-mod clause (:816-819), numeric-specialized clause (:820-843), runtime-guarded mod clause (:844-871), catch-all (:872-873); `unary_expression/3` (:875-893); `numeric_expression?/1` (:895-901); `materialize_expression/2` (:921-936) + `simple_expression?/1` (:938-943); `put_tuple/3` (:945-953) + `tuple_update/3` (:955-960); `lower/3` vs `lower_region/3` tuple_mode split (:49-55).
**Signature:** `binary_expression(name, left_expr, right_expr, pc) :: abstract_form`; `tuple_update(:beam | :runtime, tuple, index, value) :: abstract_form`.
**Data Shape:** three outcomes per binary op: (a) both operands statically numeric (literals or `+ - *` op trees over them) → inline BEAM `{:op, …}`; (b) otherwise → anonymous fn with a GUARDED clause (`is_number(l), is_number(r)` → inline op) and an unguarded fallback clause calling `Runtime.binary(name, l, r)`; (c) `mod` additionally gets a compile-time clause for integer divisor ≠ 0 → `erlang:rem`, and its runtime guarded clause requires `is_integer` on both AND `r != 0`.

### Decisive source
```elixir
defp binary_expression(name, left, right, pc)
     when name in [:add, :sub, :mul, :lt, :lte, :gt, :gte, :eq, :neq, :strict_eq, :strict_neq] do
    operator = binary_operator(name)

    if numeric_expression?(left) and numeric_expression?(right) do
      operation(operator, left, right)
    else
      left_var = variable(elem(@left_variables, rem(pc, 256)))
      right_var = variable(elem(@right_variables, rem(pc, 256)))
      guards = [[guard_call(:is_number, [left_var]), guard_call(:is_number, [right_var])]]

      anonymous_call(
        [
          guarded_clause([left_var, right_var], guards, [operation(operator, left_var, right_var)]),
          clause(
            [left_var, right_var],
            [remote_call(Runtime, :binary, [atom(name), left_var, right_var])]
          )
        ],
        [left, right]
      )
    end
  end

defp materialize_expression(state, expression) do
    if simple_expression?(expression) do
      {expression, state}
    else
      ordinal = Map.get(state.materialization_counts, state.pc, 0)
      index = rem(state.pc, 256) + ordinal * 256
      value = variable(elem(@materialized_variables, index))
      # ... bound via match expression into the block form ...
  end

defp tuple_update(:beam, tuple, index, value),
    do: remote_call(:erlang, :setelement, [integer(index + 1), tuple, value])

defp tuple_update(:runtime, tuple, index, value),
    do: remote_call(Runtime, :tuple_put, [tuple, integer(index), value])
```

**Flow:** every `{value, name, []}` op lowers through `binary_expression`/`unary_expression` → static-numeric check (`numeric_expression?` recurses only through `+ - *` op trees, so `x + 1` where x is a variable is NOT statically numeric) → inline or guard-fallback fn → result passes through `materialize_expression`, which binds any non-simple expression to a `CompilerMaterializedN` variable (index `rem(pc,256) + ordinal*256`, 512-var pool) so each complex sub-expression evaluates exactly once per block. Local/arg writes go through `put_tuple`, whose update primitive depends on `tuple_mode`: full-function lowering (`lower/3`) uses `erlang:setelement`; region lowering (`lower_region/3`, used by `Pure.prepare_region/3`) uses `Runtime.tuple_put` because regions can exit at EARLY boundaries where the runtime-owned tuple representation must stay valid.
**Invariant:** (1) Semantics are NEVER duplicated: the fallback arm of every specialized op calls the same `Runtime.binary`/`Runtime.unary` helper the interpreter uses — specialization changes speed, never meaning. (2) The guard set is deliberately narrower than the fast-path condition: `mod` guards on `is_integer` + non-zero even though JS `%` accepts numbers, so any case BEAM cannot compute natively falls through to the canonical helper instead of raising. (3) Materialization is per-pc and ordinal-bounded: the same pc can materialize up to 256 distinct expressions before wrapping, and the pool (512 vars) plus the ≤64-op eligibility cap keep the generated block form finite. (4) Region mode and function mode differ ONLY in the tuple-update primitive — everything else (charging, deopt, invocation) is shared.
**Probe:** `grep -n 'defp tuple_update' lib/quickbeam/vm/compiler/profile/scalar.ex` → 2 hits (:955 beam / :958 runtime); `grep -n 'defp materialize_expression\|defp simple_expression?' lib/quickbeam/vm/compiler/profile/scalar.ex` → 3 hits (:921/:938/:943).
**Probe:** `test/vm/compiler/profile/pure_test.exs:90-107` — "extracts a bounded scalar entry region from an oversized function": a 100-statement function yields `{:skip, 3}` from `prepare/3` but `{:ok, region_template, 32}` from `prepare_region/3` with `block/3` clauses ≤ 17 — the region path (tuple_mode :runtime) is exercised end-to-end here.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "quickbeam", query: "Scalar binary_expression unary_expression materialize_expression tuple_update", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the guard-fallback specialization pattern for any codegen tier: inline the fast op only under a guard that is STRICTLY sufficient for native computation, and make the unguarded fallback call the canonical interpreter helper rather than a reimplementation; adopt per-pc ordinal materialization to guarantee single evaluation of complex sub-expressions; adapt the two-mode tuple-update split if your tier has both whole-function and partial-region artifacts; omit QuickBEAM's compile-time constant-mod shortcut unless your target language distinguishes integer division semantics. Evidence note: mined this pass via direct whole-file source + test read fallback (Codebase Memory MCP not connected in session); probes executed byte-for-byte, Retrieve not executed.
