<!-- capsule-v2 -->
# symbol-identity-three-arm-id — How do you make JS symbol equality exact and `Symbol.for` registry-global without a central registry process?

**Source:** QuickBEAM MIT `master@c21c0e315213d0801950aae48cccedb3051c32d8`; Codebase Memory `quickbeam` (not connected in-session — direct source+test read fallback). **Question:** How do you represent JS symbols so `===` is struct equality, well-known symbols are stable, and `Symbol.for` is global — with no registry process and no leak across evaluations?

## Three-arm symbol id seam
**Path/Symbol:** `lib/quickbeam/vm/runtime/symbol.ex` (15L whole, struct + `iterator/0` :13-14); registry + fresh-symbol constructors `lib/quickbeam/vm/builtin/symbol.ex` (33L whole, `for_symbol/1` :16-19, `call/1` :22-33); counter field `lib/quickbeam/vm/runtime/state.ex` `next_symbol_id: 0` (:35, type :85); property-key consumption `lib/quickbeam/vm/runtime/opcode/object.ex` (:99/:112/:133 `%Symbol{}` on the stack as a key); export rejection `lib/quickbeam/vm/runtime/value/export.ex:50` (`convert(%Symbol{}, ...) → {:error, :symbol_result}`).
**Signature:** `Symbol.iterator() :: t()`; `QuickBEAM.VM.Builtin.Symbol.for_symbol(%Call{}) :: {:ok, t(), State.t()}`; `call(%Call{}) :: {:ok, t(), State.t()}`.
**Data Shape:** `%Symbol{id, description}` where `id` is `:iterator | {:global, String.t()} | {:local, non_neg_integer()}`. Equality is plain struct equality: two symbols are `===` iff their ids are equal. `description` is display-only and does NOT participate in identity.

### Decisive source
```elixir
# runtime/symbol.ex — the whole identity model
@enforce_keys [:id, :description]
defstruct [:id, :description]
@type t :: %__MODULE__{id: :atom() | {:global, String.t()} | {:local, non_neg_integer()},
                       description: String.t()}
def iterator, do: %__MODULE__{id: :iterator, description: "Symbol.iterator"}

# builtin/symbol.ex — Symbol.for is a pure function of the string key
def for_symbol(%Call{arguments: arguments, execution: execution}) do
  key = arguments |> List.first(:undefined) |> Value.to_string_value()
  {:ok, %Symbol{id: {:global, key}, description: key}, execution}
end

# builtin/symbol.ex — Symbol() mints a per-evaluation unique id from State
def call(%Call{arguments: arguments, execution: execution}) do
  id = execution.next_symbol_id
  description = case arguments do
    [value | _] when value != :undefined -> Value.to_string_value(value)
    _arguments -> ""
  end
  symbol = %Symbol{id: {:local, id}, description: description}
  {:ok, symbol, %{execution | next_symbol_id: id + 1}}
end
```

**Flow:** `Symbol("d")` → `{:local, n}` from the evaluation-local `State.next_symbol_id` counter, then the counter increments — unique within one evaluation, never equal across evaluations. `Symbol.for("k")` → `{:global, "k"}` — a pure function of the key, so any two evaluations in the process produce equal structs without shared mutable state. `Symbol.iterator` → the atom id `:iterator`, a compile-time constant used as a property key by `iterator.ex:141`, aliased by `builtin/map.ex:32` (`entries`) and `builtin/set.ex:29` (`values`). Property reads/writes accept `%Symbol{}` keys directly on the stack (`opcode/object.ex`); `Value.typeof/1` → `"symbol"`; exporting a symbol across the evaluation boundary is a typed failure (`:symbol_result`), never a silent coercion.
**Invariant:** identity must never depend on `description` (two `Symbol("x")` calls are never equal) and must never allocate process-wide state — the global arm works because the id IS the registry. The counter lives in `State`, so it is captured inside continuations/coroutines and serialized with the evaluation; a resumed evaluation keeps its counter, and a fresh evaluation starts at 0 (its `{:local, 0}` can never collide with another evaluation's symbols because struct equality is only ever compared within one evaluation's heap).
**Probe:** `test/vm/runtime/value_test.exs` :30-31 — `Value.typeof(Symbol.iterator()) == "symbol"` and `Value.strict_equal?(Symbol.iterator(), Symbol.iterator())` (struct equality IS JS `===` for symbols). `test/vm/runtime/promise_test.exs` :77-81 — native-parity sources exercising `[Symbol.iterator]` getters/throws through the iterator protocol that consumes the well-known symbol.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "quickbeam", query: "Symbol iterator for_symbol next_symbol_id global local id", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three-arm id: an atom for well-known symbols, `{:global, key}` for the registry (identity by construction, no registry process), `{:local, counter}` for fresh symbols with the counter in evaluation state. Adapt the arm set to your host (e.g. add a cross-evaluation namespace if your heap is shared). Omit any ETS/GenServer symbol registry — it would break the captured-in-continuation property. Caveat: no dedicated symbol_test.exs; coverage is via value_test assertions + promise_test native-parity sources + the builtin's own unit surface (direct-read fallback, no graph coverage check in-session).
