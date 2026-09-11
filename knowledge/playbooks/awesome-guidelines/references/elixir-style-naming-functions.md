<!-- capsule-v2 -->
# Naming — do atoms, functions, and exceptions follow Elixir conventions?

**Source:** elixir_style_guide §Naming; Elixir naming conventions. **Question:** Are modules, predicates, and errors named predictably?

## Identifier seam
**Path/Symbol:** modules, functions, guards, exceptions.
**Signature:** CamelCase modules; snake_case functions/vars/atoms.
**Data Shape:** `?` predicates; `is_` guards; `Error` exceptions.

### Decisive pattern
```elixir
defmodule MyApp.HTTPClient do
  def cool?(value), do: String.contains?(value, "cool")

  defguard is_ok(term) when term == :ok

  def fetch!(url), do: ...
end

defmodule MyApp.BadHTTPCodeError do
  defexception message: "bad http code"
end
```

**Flow:** modules `CamelCase` with acronym caps (`SomeXML`) → functions/vars `snake_case` → boolean returns end with `?` → guard-safe macros `is_*` via `defguard` → exception modules end with `Error` → main struct type named `@type t`.
**Invariant:** `:SomeAtom`, `someFunction`, `BadHTTPCodeException`, or `isCool` guard fail review.
**Probe:** Credo naming cops; code review checklist.

## Private/public seam
```elixir
def sum(list), do: sum_total(list, 0)

defp sum_total([], total), do: total
defp sum_total([head | tail], total), do: sum_total(tail, head + total)
```

**Flow:** private helpers use distinct descriptive names — avoid `def foo` + `defp do_foo` pattern and never same name public/private.
**Invariant:** `def process` + `defp do_process` pairing fails review.
**Probe:** grep `defp do_` prefix pattern.

## Verdict
CamelCase modules, snake_case functions, ?/is_/Error conventions. Learning note: `elixir-style-learning-note.md`.
