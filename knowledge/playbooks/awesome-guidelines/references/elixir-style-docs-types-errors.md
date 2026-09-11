<!-- capsule-v2 -->
# Docs, types, and errors — are contracts and failures documented?

**Source:** elixir_style_guide §Documentation, §Typespecs, §Exceptions, §Testing. **Question:** Do public modules carry docs, specs, and consistent errors?

## Documentation seam
**Path/Symbol:** exported modules and functions.
**Signature:** `@moduledoc`; `@doc`; `@spec` before `def`.
**Data Shape:** `@typedoc` + `@type` pairs; `@type t` for main struct.

### Decisive pattern
```elixir
defmodule MyApp.Accounts.User do
  @moduledoc """
  User account operations.
  """

  @typedoc "A persisted user record."
  @type t :: %__MODULE__{
          id: pos_integer(),
          email: String.t()
        }

  @doc """
  Loads a user by email.
  """
  @spec fetch_by_email(String.t()) :: {:ok, t()} | {:error, :not_found}
  def fetch_by_email(email) do
    ...
  end
end
```

**Flow:** `@moduledoc` or `@moduledoc false` right after module line → blank line after moduledoc → `@typedoc` adjacent to `@type` → `@spec` immediately after `@doc` before `def` → name primary struct type `t`.
**Invariant:** public function without `@doc`/`@spec` (Dialyzer teams) or `@spec` separated from `def` by blank line fails review.
**Probe:** `mix dialyzer` / Credo doc cops; ExDoc build.

## Errors and tests seam
```elixir
raise ArgumentError, "invalid email format"

test "returns ok for valid token" do
  assert verify_token("valid") == :ok
end
```

**Flow:** custom exceptions end with `Error` → raise messages lowercase, no trailing period → ExUnit `assert actual == expected` (actual left) → avoid needless metaprogramming.
**Invariant:** `raise "Invalid."` capitalized or `assert expected == actual` fails review.
**Probe:** test suite style review; exception module naming grep.

## Verdict
moduledoc/spec/types, Error suffix, lowercase raises, assert order. Learning note: `elixir-style-learning-note.md`.
