<!-- capsule-v2 -->
# value-extended-number-coercion — How do you represent JavaScript numbers (NaN, ±Infinity, ±0) as BEAM terms so every arithmetic opcode is a pure pattern-match ladder that never leaks a BEAM arithmetic error?

**Source:** QuickBEAM MIT `master@c21c0e315213d0801950aae48cccedb3051c32d8`; Codebase Memory `quickbeam`. **Question:** How do you represent JavaScript numbers (NaN, ±Infinity, ±0) as BEAM terms so arithmetic never raises and IEEE edge cases stay exact?

## Extended-number value algebra seam
**Path/Symbol:** `lib/quickbeam/vm/runtime/value.ex` (441L): `truthy?/1` (:24-32), `strict_equal?/2` (:35-39), `abstract_equal?/2` (:42-57), `unary/2` (:60-70), `binary/3` (:73-97), `add/2` (:100-102), `divide_numbers/2` ladder (:131-152), `remainder/2` ladder (:160-176), `typeof/1` (:247-262), `to_number/1` (:265-282), `to_int32/1` (:285-293), `to_string_value/1` (:296-312), `parse_number/1` (:319-339), `power_numbers/2` + `power_infinite_*` (:402-434), `negate_number/1` (:436-441), `negative?/1` IEEE sign read (:464-471), `signed32/1` (:479-482). Consumers: `opcode/value.ex` dispatch lists (:18-48) and `interpreter.ex` value-opcode arm (:386).
**Signature:** `binary(atom(), term(), term()) :: term()`; `to_number(term()) :: number() | :nan | :infinity | :neg_infinity`; `to_int32(term()) :: integer()`; `truthy?(term()) :: boolean()`.
**Data Shape:** Numbers are Elixir integers/floats PLUS three sentinel atoms `:nan`, `:infinity`, `:neg_infinity`; negative zero is the float `-0.0` (sign inspected via `<<sign::1, _::63>> = <<value::float>>`). All operations are total: they return sentinel atoms instead of raising.

### Decisive source
```elixir
defp divide_numbers(dividend, divisor)
     when dividend in [:infinity, :neg_infinity] and is_number(divisor),
     do: signed_infinity(negative?(dividend) != negative?(divisor))

defp divide_numbers(dividend, divisor) when dividend == 0 and divisor == 0, do: :nan

defp negative?(value) when is_float(value) and value == 0.0 do
  <<sign::1, _magnitude::63>> = <<value::float>>
  sign == 1
end

defp power_numbers(base, exponent) do
  :math.pow(base, exponent)
rescue
  ArithmeticError -> :nan
end
```

**Flow:** an arithmetic opcode (`:add`…`:shr`) dispatches through `Value.binary/3` → each family runs a clause ladder over the extended-number domain (`add_numbers`, `divide_numbers`, `remainder`, `multiply_numbers`, `power_numbers`) → coercion happens first (`to_number/1` trims strings, parses `0x/0b/0o` prefixes, maps `nil→0`, `:undefined→:nan`) → bitwise/shift families coerce through `to_int32/1` (mask to 32 bits, wrap at `0x80000000`) with shift counts masked `band(…, 31)` → comparisons order strings lexically and everything else numerically with NaN-poisoned results → the interpreter consumes the returned term directly; a sentinel flows back onto the value stack like any number.
**Invariant:** no arithmetic operation can raise a BEAM error — every clause is total over the extended domain; `-0.0` is preserved through `modulo` and `negate` (sign read from the IEEE bit pattern, not `value < 0`); `strict_equal?(:nan, :nan)` is false while `a === b` handles all other terms.
**Probe:** `test/vm/runtime/value_test.exs` (117L) — `Value.binary(:div, 1, -0.0) == :neg_infinity`, `binary(:mod, -4, 2)` asserted negative via `<<1::1, _::63>> = <<…::float>>`, `binary(:pow, -1, :infinity) == :nan`, `to_int32(0xFFFFFFFF) == -1`; end-to-end `test/vm/runtime/value_test.exs:66-79` compiles a 11-expression extended-number program and asserts the exact result list including `negative_zero`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "quickbeam", query: "to_number divide_numbers signed_infinity negative zero to_int32 Value.binary", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the extended-number convention (sentinel atoms + IEEE-bit negative zero) and the total-clause-ladder style — it is what lets an interpreter run untrusted arithmetic without try/rescue on every opcode. Adopt `to_int32` masking and the shift-count `band(…, 31)` rule verbatim. Adapt `parse_number/1`'s prefix set to your host's numeric-literal grammar. Omit the `power/2` rescue only if your host exponentiation is already total. Caveat: direct-read fallback (Codebase Memory MCP not connected this session); `to_string_value` float formatting beyond the integral-range fast path is covered only by the `1.0 → "1"` test assertion.
