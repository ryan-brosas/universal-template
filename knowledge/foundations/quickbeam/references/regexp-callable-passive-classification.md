<!-- capsule-v2 -->
# regexp-callable-passive-classification — How do you represent compiled-regex values and callable classification as passive data so property reads never execute JS?

**Source:** QuickBEAM MIT `master@c21c0e315213d0801950aae48cccedb3051c32d8`; Codebase Memory `quickbeam` (not connected in-session — direct source+test read fallback). **Question:** How do regex values reach the regex engine, and how does `typeof f === "function"` get answered, when the runtime refuses to run JS during a property read?

## Passive regexp record + 3-clause callable classifier seam
**Path/Symbol:** `lib/quickbeam/vm/runtime/regexp.ex` (8L whole); allocation `lib/quickbeam/vm/runtime/opcode/object.ex` `:regexp` arm (:74-79, `Heap.allocate(execution, :regexp, internal: %RegExp{...})` + `lastIndex` define); bytecode origin `lib/quickbeam/vm/bytecode/decoder.ex:310-313` (`@tag_regexp` object literal in decoded constants); method dispatch `lib/quickbeam/vm/runtime/property.ex` (:44-45 `%RegExp{}` receiver → `{:primitive_method, :regexp, key}`, :88-89 `exec`/`test` on `kind: :regexp` objects); classifier `lib/quickbeam/vm/runtime/callable.ex` (36L whole, `@callable_tags` :12-19, `typeof/2` :27-35); heap-object callable flag `lib/quickbeam/vm/builtin/runtime.ex:24-29`; identity backdrop `lib/quickbeam/vm/runtime/reference.ex` (8L whole, `%Reference{id}` — the sole heap identity, 104 pattern sites across lib).
**Signature:** `Callable.callable?(term(), State.t()) :: boolean()`; `Callable.typeof(term(), State.t()) :: String.t()`; `Property.get(%RegExp{}, key, _execution) :: {:ok, {:primitive_method, :regexp, key}}`.
**Data Shape:** `%RegExp{source, bytecode}` — `bytecode` is QuickJS libregexp bytecode compiled at bytecode-DECODE time (a `@tag_regexp`-tagged constant inside the program), never at property-read time. `%Reference{id: non_neg_integer()}` is the only object identity; `%RegExp{}` values are stored as heap `internal` data behind a `:regexp`-kind object.

### Decisive source
```elixir
# runtime/callable.ex — the whole classifier
@callable_tags [:builtin, :declared_builtin, :bound_function, :host_function,
                :primitive_method, :promise_resolver]
def callable?(value, execution), do: typeof(value, execution) == "function"
def typeof(%Reference{} = reference, execution) do
  if BuiltinRuntime.callable(execution, reference), do: "function", else: "object"
end
def typeof(value, _execution) when is_tuple(value) and elem(value, 0) in @callable_tags,
  do: "function"
def typeof(value, _execution), do: Value.typeof(value)

# runtime/property.ex — regex method reads return a PLAN, never execute
def get(%RegExp{}, key, _execution) when is_binary(key),
  do: {:ok, {:primitive_method, :regexp, key}}
```

**Flow:** `/pattern/flags` in source → bytecode decoder emits a `{:regexp, source, bytecode}` constant → `:regexp` opcode allocates a `:regexp`-kind heap object with `%RegExp{}` as internal data plus a writable `lastIndex` data property → `re.exec`/`re.test` reads return `{:primitive_method, :regexp, key}` — an action the interpreter later executes against the priv/c_src libregexp NIF; the read itself touches no JS. Callable classification is the same discipline: a value is `"function"` iff it is a heap object whose stored `callable` flag is truthy (one heap fetch) or a tagged tuple whose tag is in the closed six-tag list; everything else falls to `Value.typeof/1`. `Callable.callable?/2` is the thenable gate used by `promise.ex:307` before treating a value as a then-function.
**Invariant:** property reads and typeof must stay non-executing and non-blocking — regex execution and function invocation are separate planned actions. The `@callable_tags` list is closed: adding a new callable representation means extending the list AND every consumer that pattern-matches the tags, not adding a dynamic check. `%Reference{}` equality is identity; `%RegExp{}` is data (two structurally equal regexes are still distinct objects because they live behind distinct references).
**Probe:** `test/vm/runtime/interpreter_test.exs` :109-115 — `QuickBEAM.VM.compile("/beam/.test('quickbeam')")` → `{:ok, true}`, plus a global-flag regex (the `lastIndex` statefulness path). `test/web_apis/web_apis_test.exs` :601-606 — `clone instanceof RegExp && clone.source === 'test'` (source survives as data). `test/vm/runtime/opcode_test.exs` :192-204 — `Values.execute(:is_function, ...)` over an allocated `:function` object → `true` (the heap-flag arm of the classifier).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "quickbeam", query: "RegExp primitive_method callable_tags typeof Reference heap identity", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt passive-value discipline: regexes as {source, precompiled bytecode} records allocated as ordinary heap objects with plan-returning method reads; callable classification as a closed tag list + one heap-flag fetch, never a probe call. Adapt the bytecode format (QuickJS libregexp bytecode is QuickBEAM-specific — your host compiles its own regex IR) and the tag list to your callable taxonomy. Omit eager regex compilation at property-read time and any typeof that executes JS. Caveat: no dedicated regexp_test.exs or callable_test.exs; coverage is via interpreter_test/web_apis/opcode_test ranges (direct-read fallback, no graph coverage check in-session). `%Reference{}` and `%Frame.Native{}` are folded here as backdrop: Reference is the identity primitive every heap consumer shares; Frame.Native (see continuation capsule cross-reference) is the resumable native-callback record that appears in caller stacks.
