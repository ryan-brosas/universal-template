<!-- capsule-v2 -->
# Formatting and modules — is mix format applied and module layout ordered?

**Source:** elixir_style_guide §Formatting, §Modules. **Question:** Will formatter and module skeleton match community norms?

## Format seam
**Path/Symbol:** `.ex`/`.exs` files in Mix projects.
**Signature:** `mix format`; ≤98 columns; Unix newlines.
**Data Shape:** module attribute order per guide.

### Decisive pattern
```elixir
defmodule MyApp.Parser.Core.XMLParser do
  @moduledoc """
  Parses XML payloads for the core parser pipeline.
  """

  @behaviour MyApp.Parser

  use GenServer

  alias MyApp.Long.Module.Name

  @type t :: %__MODULE__{buffer: binary()}

  @spec parse(binary()) :: {:ok, map()} | {:error, term()}
  def parse(data) do
    data
    |> normalize()
    |> decode()
  end
end
```

**Flow:** run `mix format` on every change → limit lines to 98 cols → file `parser/core/xml_parser.ex` nests `Parser.Core.XMLParser` → `@moduledoc` immediately after `defmodule` → order: behaviour, use, import/require, alias, types, callbacks, defs (alphabetical within groups).
**Invariant:** unformatted diff, `@moduledoc` after `use`, or flat filename for nested module fails review.
**Probe:** `mix format --check-formatted`; module skeleton lint / Credo module order cops.

## File naming seam
**Flow:** `snake_case.ex` mirrors `CamelCase` module → one module per file → avoid repetitive namespaces (`Todo.Item` not `Todo.Todo`).
**Invariant:** `SomeModule.ex` filename or duplicate namespace fragment fails review.
**Probe:** path/module name alignment check in CI.

## Verdict
mix format, 98 cols, @moduledoc-first ordered modules, snake_case paths. Learning note: `elixir-style-learning-note.md`.
