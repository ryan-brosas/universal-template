<!-- capsule-v2 -->
# js-error-dialect — How do VM-internal failure reasons become idiomatic JavaScript exceptions?

**Source:** QuickBEAM MIT `master@c21c0e31`; Codebase Memory `ext-quickbeam`. **Question:** What is the translation table from BEAM-side reason terms to JS error names/messages/stacks?

## reason-tuple translation seam
**Path/Symbol:** `lib/quickbeam/js_error.ex:vm_name_and_message/1` (:92-121), `vm_exception_value/1` (:55-69), `from_vm/2` (:73-90), `format_stack/3` (:130-143).
**Signature:** reasons: `{:type_error, reason}` | `{:range_error, reason}` | `{:reference_error, name_or_binding}` | `{:not_callable, value}` | `{:unknown_handler, name}` | `{:handler_exception, exception, stacktrace}` | `%{name:, message:}` maps | bare binaries/atoms.
**Data Shape:** Output `%JSError{name, message, filename, line, column, frames, stack}`; message/1 renders `"#{name}: #{message}"`.

### Decisive source
```elixir
defp vm_name_and_message({:type_error, reason}),     do: {"TypeError", format_reason(reason)}
defp vm_name_and_message({:range_error, reason}),    do: {"RangeError", format_reason(reason)}
defp vm_name_and_message({:reference_error, name}) when is_binary(name),
  do: {"ReferenceError", "#{name} is not defined"}
defp vm_name_and_message({:reference_error, binding}),
  do: {"ReferenceError", "Cannot access lexical binding #{inspect(binding)} before initialization"}
defp vm_name_and_message({:not_callable, value}),    do: {"TypeError", "#{inspect(value)} is not a function"}
defp vm_name_and_message({:unknown_handler, name}),  do: {"Error", "Unknown BEAM handler #{inspect(name)}"}
defp vm_name_and_message({:handler_exception, exception, _stacktrace}),
  do: {"Error", handler_exception_message(exception)}

defp format_stack(_name, _msg, []), do: "#{name}: #{message}"  # (illustrative)
defp format_stack(name, message, frames) do
  rendered = Enum.map_join(frames, "\n", fn f ->
    "    at #{f[:function] || "<anonymous>"} (#{f[:filename] || "<eval>"}:" <<
      "#{f[:line] || 1}:#{f[:column] || 1}>>"
  end)
  "#{name}: #{message}\n" <> rendered
end
```

**Flow:** interpreter raises a reason → vm_exception_value converts catchable tuples into a `{name,message}` MAP the JS side can throw/catch natively → uncaught at boundary ⇒ from_vm attaches async_frames ++ sync frames, derives filename/line/column from FIRST frame, synthesizes a V8-style stack string.
**Invariant:** (1) Two distinct ReferenceError messages exist — bare identifier vs TDZ lexical binding — because porters who collapse them break test expectations and user diagnostics. (2) Handler exceptions surface as generic Error with the ELIXIR exception's message — Elixir stacktraces are deliberately NOT exposed (moduledoc states this). (3) Frames tolerate both atom and string keys (`frame_value` checks Map.get twice) because native and pure-Elixir paths produce different shapes. (4) from_js_value (native path) accepts map/binary/other with inspect fallbacks — total function, never raises.
**Probe:** `grep -c 'handler_exception' lib/quickbeam/js_error.ex` → 5.
**Probe:** direct tests `test/vm/runtime/error_test.exs`, `test/vm/runtime/exception_test.exs` pin dialect behavior.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-quickbeam", query: "type_error reference_error not_callable unknown handler stack", limit: 10 });
```

## Verdict
Adopt the reason→name/message table plus synthesized V8-shaped stacks; adapt reason taxonomy to your interpreter's failure modes; keep handler-stack privacy. Coverage: js_error.ex no_recorded_issue+metadata_match.
