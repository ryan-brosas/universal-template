<!-- capsule-v2 -->
# Expressions and pipelines — is control flow idiomatic and pipes purposeful?

**Source:** elixir_style_guide §Expressions, §Collections. **Question:** Are pipelines multi-step and conditionals readable?

## Pipeline seam
**Path/Symbol:** function bodies transforming data.
**Signature:** `|>` chains with bare first argument; no one-step pipes.
**Data Shape:** keyword list `[key: val]` syntax.

### Decisive pattern
```elixir
def sanitize_email(email) do
  email
  |> String.downcase()
  |> String.trim()
end

if success do
  :ok
else
  {:error, reason}
end

cond do
  expired?(token) -> {:error, :expired}
  true -> :ok
end

opts = [timeout: 5000, active: true]
```

**Flow:** put subject first in pipe chain → only pipe when ≥2 steps → use `def foo(arg)` with parens, `def foo` without when zero arity → never `unless ... else` → `cond` fallback is `true` → keyword lists use shorthand syntax.
**Invariant:** `String.downcase(x)` as single pipe, `unless ... else`, or `:else` in `cond` fails review.
**Probe:** Credo pipe cops; readability review on new functions.

## Def clause seam
```elixir
def handle(nil), do: {:error, "missing"}
def handle([]), do: :ok

def handle([head | rest]) do
  process(head)
  handle(rest)
end
```

**Flow:** group single-line `def` clauses; separate multiline defs with blank line; if any multiline clause exists, avoid mixing single-line defs for same function.
**Invariant:** mixed single/multiline `def` style for same function fails review.
**Probe:** function clause layout review.

## Verdict
Multi-step pipes, positive if/else, true cond, keyword syntax. Learning note: `elixir-style-learning-note.md`.
